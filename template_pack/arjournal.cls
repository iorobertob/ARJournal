\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{arjournal}[2026/04/11 Trans/Act Artistic Research Journal class]

\LoadClass[12pt]{article}

% ── Core packages ─────────────────────────────────────────────────────────────
\RequirePackage[utf8]{inputenc}
\RequirePackage[T1]{fontenc}
\RequirePackage{lmodern}
\RequirePackage[a4paper,margin=1in]{geometry}
\RequirePackage{graphicx}
\RequirePackage{xcolor}
\RequirePackage{longtable}
\RequirePackage{booktabs}
\RequirePackage{array}
\RequirePackage{enumitem}
\RequirePackage{caption}
\RequirePackage{ifthen}
\RequirePackage{etoolbox}
\RequirePackage{fancyhdr}
\RequirePackage{titlesec}
\RequirePackage{setspace}
\RequirePackage{microtype}      % improved justification and hyphenation

% ── Quotation handling ────────────────────────────────────────────────────────
% csquotes provides \enquote{} for language-aware inline quotation marks.
% Use \enquote{text} for short quotations (under 40 words / 4 lines).
% The platform parser converts \enquote{} to typographic curly quotes " ".
\RequirePackage[autostyle=true]{csquotes}

% ── Bibliography — Cambridge author–date ("CambridgeA") ────────────────────────
% The journal uses the Cambridge author–date reference system. Cite sources
% parenthetically by author surname + year with NO comma between them, and list
% all works in a section headed "References".
%   \citep{key}        parenthetical: (Smith 2024)
%   \citet{key}        narrative:     Smith (2024)
%   \citep[47]{key}    with page:     (Smith 2024, 47)
%   \citep{a,b}        multiple:      (Smith 2024; Brown 2022)
%   \cite{key}         alias for \citep{key}
\RequirePackage[authoryear,sort&compress]{natbib}
% Cambridge in-text style: no comma between author and year; ";" between refs.
\setcitestyle{aysep={},citesep={;}}
% The reference list is always headed "References".
\renewcommand{\refname}{References}
\renewcommand{\bibname}{References}
% NOTE: the local PDF is an author–year *draft preview*. The published HTML article
% is rendered by the platform in full Cambridge (CambridgeA) formatting — authors in
% bold "Surname Initials", sentence-case article titles, italic book/journal titles,
% "Place: Publisher", DOIs — from your .bib. Follow the Cambridge examples when you
% fill in the .bib so the published references are complete.
% \bibliographystyle is set in the document (see arjournal_template.tex).

% ── Hyperlinks ────────────────────────────────────────────────────────────────
\RequirePackage{hyperref}
\hypersetup{
  colorlinks=true,
  linkcolor=black,
  urlcolor=[rgb]{0.33,0.33,0.33},
  citecolor=black,
  pdftitle={},
  pdfauthor={}
}

% ── Page style ────────────────────────────────────────────────────────────────
\pagestyle{fancy}
\fancyhf{}
\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0pt}

% ── Section formatting ────────────────────────────────────────────────────────
\titleformat{\section}{\large\bfseries}{\thesection.}{0.5em}{}
\titleformat{\subsection}{\normalsize\bfseries}{\thesubsection.}{0.5em}{}
\titleformat{\subsubsection}{\normalsize\itshape}{\thesubsubsection.}{0.5em}{}

% ── Metadata command declarations ─────────────────────────────────────────────
\newcommand{\ARJtitle}[1]{\def\@ARJtitle{#1}}
\newcommand{\ARJsubtitle}[1]{\def\@ARJsubtitle{#1}}
\newcommand{\ARJauthor}[1]{\def\@ARJauthor{#1}}
\newcommand{\ARJaffiliation}[1]{\def\@ARJaffiliation{#1}}
\newcommand{\ARJemail}[1]{\def\@ARJemail{#1}}
\newcommand{\ARJORCID}[1]{\def\@ARJORCID{#1}}
\newcommand{\ARJkeywords}[1]{\def\@ARJkeywords{#1}}
\newcommand{\ARJabstract}[1]{\def\@ARJabstract{#1}}
\newcommand{\ARJacknowledgements}[1]{\def\@ARJacknowledgements{#1}}
\newcommand{\ARJfunding}[1]{\def\@ARJfunding{#1}}
\newcommand{\ARJconflicts}[1]{\def\@ARJconflicts{#1}}
\newcommand{\ARJlicense}[1]{\def\@ARJlicense{#1}}
\newcommand{\ARJarticleType}[1]{\def\@ARJarticleType{#1}}

% Default values
\def\@ARJtitle{}
\def\@ARJsubtitle{}
\def\@ARJauthor{}
\def\@ARJaffiliation{}
\def\@ARJemail{}
\def\@ARJORCID{}
\def\@ARJkeywords{}
\def\@ARJabstract{}
\def\@ARJacknowledgements{}
\def\@ARJfunding{}
\def\@ARJconflicts{}
\def\@ARJlicense{}
\def\@ARJarticleType{}

% ── Blind review mode ─────────────────────────────────────────────────────────
% \ARJblindreview redacts all author-identifying fields in the PDF.
% The platform also uses this flag to strip author data from the review copy.
\newif\ifarjblind
\arjblindfalse
\newcommand{\ARJblindreview}{\arjblindtrue}

\AtBeginDocument{
  \ifarjblind
    \def\@ARJauthor{[redacted for review]}
    \def\@ARJaffiliation{[redacted for review]}
    \def\@ARJemail{[redacted for review]}
    \def\@ARJORCID{[redacted for review]}
  \fi
}

% ── Title block ───────────────────────────────────────────────────────────────
\newcommand{\makearjtitle}{
  \begin{center}
    {\LARGE \bfseries \@ARJtitle \par}
    \ifthenelse{\equal{\@ARJsubtitle}{}}{}{
      \vspace{0.3em}
      {\large \itshape \@ARJsubtitle \par}
    }
    \vspace{1em}
    {\normalsize \@ARJauthor \par}
    {\small \@ARJaffiliation \par}
    \ifarjblind\else
      {\small \href{mailto:\@ARJemail}{\@ARJemail} \par}
      \ifthenelse{\equal{\@ARJORCID}{}}{}{
        {\small ORCID: \href{https://orcid.org/\@ARJORCID}{\@ARJORCID} \par}
      }
    \fi
    \vspace{0.6em}
    {\small \textit{Article type:} \@ARJarticleType \par}
  \end{center}
  \vspace{1em}
  \noindent\textbf{Abstract.}\ \@ARJabstract\par
  \vspace{0.4em}
  \noindent\textbf{Keywords.}\ \@ARJkeywords\par
  \vspace{1.2em}
  \hrule
  \vspace{1em}
}

% ── Media macros ─────────────────────────────────────────────────────────────
% These macros create placeholders in the compiled PDF and reference
% the uploaded asset files. The platform uses the arguments to build
% HTML5 video/audio elements and manage asset rights.

% \ARJfigure[label]{filename}{caption}{alt text for accessibility}
%
% Optional first argument [label]: a short key for cross-referencing.
%   Omit the "fig:" prefix — it is added automatically.
%   Reference in text as:  Figure~\ref{fig:label}
%   If omitted, an automatic label is derived from the filename.
%
% filename: the image file you upload to the platform (e.g. figure1.jpg)
% caption:  displayed below the image
% alt text: machine-readable description for accessibility and parsing
%
% Examples:
%   \ARJfigure[boundary]{figure1.jpg}{Caption.}{Alt text.}
%   → reference as Figure~\ref{fig:boundary}
%
%   \ARJfigure{figure1.jpg}{Caption.}{Alt text.}
%   → auto-label; reference as Figure~\ref{fig:figure1.jpg}
\newcommand{\ARJfigure}[4][]{%
  \begin{figure}[ht]
    \centering
    \includegraphics[width=\linewidth]{#2}
    \caption{#3}
    \ifthenelse{\equal{#1}{}}{\label{fig:#2}}{\label{fig:#1}}
  \end{figure}%
  % Parser reads alt text from arg #4 and optional label from arg #1
}

% \ARJlogo[label]{filename}{caption}{alt text}
%
% Same as \ARJfigure but for a LOGO or ICON: displayed small (not stretched to
% the text width) here and in the published HTML. Upload the image at its
% natural size, ≤ 300×300 px. Use \ARJfigure for normal content images.
\newcommand{\ARJlogo}[4][]{%
  \begin{figure}[ht]
    \centering
    \includegraphics[width=0.3\linewidth]{#2}
    \caption{#3}
    \ifthenelse{\equal{#1}{}}{\label{fig:#2}}{\label{fig:#1}}
  \end{figure}%
  % Parser reads alt text from arg #4 and tags this figure role="logo"
}

% \ARJvideo[label]{filename}{caption}{poster image}{transcript file}
%
% Optional first argument [label]: reference as Figure~\ref{fig:label}
% poster image: a still frame displayed before playback (upload separately)
% transcript:   VTT or plain-text transcript asset key (upload separately)
\newcommand{\ARJvideo}[5][]{%
  \begin{figure}[ht]
    \centering
    \fbox{\parbox{0.9\linewidth}{%
      \textbf{[Video: #3]}\par
      \smallskip
      \noindent Asset: {\ttfamily\detokenize{#2}} \quad Poster: {\ttfamily\detokenize{#4}}\par
      \noindent Transcript: {\ttfamily\detokenize{#5}}%
    }}
    \caption{#3}
    \ifthenelse{\equal{#1}{}}{}{\label{fig:#1}}
  \end{figure}%
}

% \ARJaudio[label]{filename}{caption}{transcript file}
%
% Optional first argument [label]: reference as Figure~\ref{fig:label}
\newcommand{\ARJaudio}[4][]{%
  \begin{figure}[ht]
    \centering
    \fbox{\parbox{0.9\linewidth}{%
      \textbf{[Audio: #3]}\par
      \smallskip
      \noindent Asset: {\ttfamily\detokenize{#2}} \quad Transcript: {\ttfamily\detokenize{#4}}%
    }}
    \caption{#3}
    \ifthenelse{\equal{#1}{}}{}{\label{fig:#1}}
  \end{figure}%
}

% \ARJembednote{assetKey}{description}
% For inline notes referencing a named asset (e.g. data appendix, score)
\newcommand{\ARJembednote}[2]{%
  \begin{quote}
    \textbf{Embedded asset note.}\ Asset key: \texttt{#1}.\quad #2
  \end{quote}%
}

% ── Declarations block ────────────────────────────────────────────────────────
\newcommand{\ARJprintdeclarations}{%
  \section*{Declarations}
  \noindent\textbf{Funding.}\ \@ARJfunding\par
  \vspace{0.4em}
  \noindent\textbf{Conflicts of interest.}\ \@ARJconflicts\par
  \vspace{0.4em}
  \noindent\textbf{License preference.}\ \@ARJlicense\par
  \ifthenelse{\equal{\@ARJacknowledgements}{}}{}{%
    \vspace{0.4em}
    \noindent\textbf{Acknowledgements.}\ \@ARJacknowledgements\par
  }%
}
