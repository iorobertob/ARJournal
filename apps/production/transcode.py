"""ffmpeg-based HLS transcoding for video & audio assets.

Produces a VOD HLS package (an `.m3u8` playlist + small `.ts` segments) so media
is streamed in pieces instead of served as one downloadable file. Video gets an
adaptive ladder (renditions capped at the source height — never upscaled); audio
gets a single AAC/HLS rendition.

Each rendition is a separate ffmpeg pass (simple, robust commands); the master
playlist is then written by hand. Slower than a single multi-output command but
far easier to reason about — fine for the once-a-year publish batch.

Requires the `ffmpeg`/`ffprobe` system binaries (installed by scripts/deploy.sh).
"""
import json
import os
import subprocess

from django.conf import settings

# Approx per-rendition video bitrate (kbps) by height.
BITRATE_KBPS = {2160: 12000, 1440: 8000, 1080: 5000, 720: 2800, 480: 1400, 360: 800, 240: 400}
AUDIO_BITRATE_KBPS = 128
SEGMENT_SECONDS = 6
FFMPEG_TIMEOUT = 60 * 60  # 1h ceiling per rendition


class TranscodeError(RuntimeError):
    pass


def _run(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT)
    if proc.returncode != 0:
        tail = (proc.stderr or '').strip().splitlines()[-6:]
        raise TranscodeError('ffmpeg failed: ' + ' | '.join(tail))


def probe(path: str) -> dict:
    """Return {width, height, duration, has_video, has_audio} via ffprobe."""
    out = subprocess.run(
        [settings.FFPROBE_BIN, '-v', 'quiet', '-print_format', 'json',
         '-show_format', '-show_streams', path],
        capture_output=True, text=True, timeout=120,
    )
    if out.returncode != 0:
        raise TranscodeError('ffprobe failed')
    data = json.loads(out.stdout or '{}')
    info = {'width': None, 'height': None, 'duration': None,
            'has_video': False, 'has_audio': False}
    for s in data.get('streams', []):
        if s.get('codec_type') == 'video' and not info['has_video']:
            info['has_video'] = True
            info['width'], info['height'] = s.get('width'), s.get('height')
        elif s.get('codec_type') == 'audio':
            info['has_audio'] = True
    try:
        info['duration'] = float(data.get('format', {}).get('duration'))
    except (TypeError, ValueError):
        pass
    return info


def _ladder_heights(src_height: int, ladder) -> list[int]:
    """Heights to produce: rungs below the source, plus a top rung capped at source."""
    rungs = sorted({h for h in ladder if h < src_height}, reverse=True)
    top = min(src_height, max(ladder))
    heights = sorted({top, *rungs}, reverse=True)
    return heights or [src_height]


def _even(n: int) -> int:
    return n - (n % 2)


def transcode(src: str, out_dir: str, is_audio: bool, ladder=None) -> dict:
    """Transcode `src` into an HLS package under `out_dir`.

    Returns {'master': <filename>, 'duration': float|None, 'renditions': [...]}.
    """
    ladder = ladder or getattr(settings, 'HLS_LADDER', [1080, 720, 360])
    os.makedirs(out_dir, exist_ok=True)
    info = probe(src)

    if is_audio or not info['has_video']:
        return _transcode_audio(src, out_dir, info)
    return _transcode_video(src, out_dir, info, ladder)


def _hls_common(seg_pattern, playlist):
    return [
        '-f', 'hls', '-hls_time', str(SEGMENT_SECONDS), '-hls_playlist_type', 'vod',
        '-hls_segment_filename', seg_pattern, playlist,
    ]


def _transcode_audio(src, out_dir, info) -> dict:
    playlist = os.path.join(out_dir, 'audio.m3u8')
    cmd = [settings.FFMPEG_BIN, '-y', '-i', src, '-vn',
           '-c:a', 'aac', '-b:a', f'{AUDIO_BITRATE_KBPS}k', '-ac', '2']
    cmd += _hls_common(os.path.join(out_dir, 'audio_%03d.ts'), playlist)
    _run(cmd)
    return {'master': 'audio.m3u8', 'duration': info.get('duration'), 'renditions': ['audio']}


def _transcode_video(src, out_dir, info, ladder) -> dict:
    src_h = info['height'] or max(ladder)
    src_w = info['width'] or src_h
    heights = _ladder_heights(src_h, ladder)
    variants = []
    for h in heights:
        w = _even(round(src_w * h / src_h))
        vbr = BITRATE_KBPS.get(h, max(400, int(5000 * h / 1080)))
        rdir = os.path.join(out_dir, f'{h}p')
        os.makedirs(rdir, exist_ok=True)
        cmd = [settings.FFMPEG_BIN, '-y', '-i', src,
               '-vf', f'scale=-2:{h}',
               '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21',
               '-maxrate', f'{vbr}k', '-bufsize', f'{vbr * 2}k',
               '-g', '48', '-keyint_min', '48', '-sc_threshold', '0',
               '-pix_fmt', 'yuv420p']
        if info['has_audio']:
            cmd += ['-c:a', 'aac', '-b:a', f'{AUDIO_BITRATE_KBPS}k', '-ac', '2']
        else:
            cmd += ['-an']
        cmd += _hls_common(os.path.join(rdir, 'seg_%03d.ts'),
                           os.path.join(rdir, 'playlist.m3u8'))
        _run(cmd)
        bandwidth = (vbr + (AUDIO_BITRATE_KBPS if info['has_audio'] else 0)) * 1000
        variants.append({'height': h, 'width': w, 'bandwidth': bandwidth})

    # Hand-write the master playlist referencing each rendition.
    lines = ['#EXTM3U', '#EXT-X-VERSION:3']
    for v in variants:
        lines.append(
            f'#EXT-X-STREAM-INF:BANDWIDTH={v["bandwidth"]},RESOLUTION={v["width"]}x{v["height"]}'
        )
        lines.append(f'{v["height"]}p/playlist.m3u8')
    with open(os.path.join(out_dir, 'master.m3u8'), 'w') as fh:
        fh.write('\n'.join(lines) + '\n')

    return {'master': 'master.m3u8', 'duration': info.get('duration'),
            'renditions': [f'{v["height"]}p' for v in variants]}
