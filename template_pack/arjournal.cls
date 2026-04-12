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

% ── Bibliography (natbib, author–year style) ───────────────────────────────────
% Use \citep{key} for parenthetical: (Smith, 2024)
% Use \citet{key} for narrative: Smith (2024)
% Use \cite{key} as an alias for \citep{key}
\RequirePackage[round,authoryear,sort&compress]{natbib}
\bibliographystyle{apalike}    % default style; override in your .tex if needed

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

% ── Blockquote environment (long quotations, 40+ words / 4+ lines) ─────────────
% Use this for extended quotations. The text is indented 0.5 in on both sides,
% set in slightly smaller type, and presented without quotation marks.
% The platform parser maps this to a <blockquote> element in HTML and applies
% 0.5 inch indentation in the PDF.
\newenvironment{ARJblockquote}{%
  \begin{quote}%
}{%
  \end{quote}%
}

% ── Media macros ─────────────────────────────────────────────────────────────
% These macros create placeholders in the compiled PDF and reference
% the uploaded asset files. The platform uses the arguments to build
% HTML5 video/audio elements and manage asset rights.

% \ARJfigure{filename}{caption}{alt text for accessibility}
% filename: the image file you upload to the platform (e.g. figure1.jpg)
% caption:  displayed below the image
% alt text: machine-readable description for accessibility and parsing
\newcommand{\ARJfigure}[3]{%
  \begin{figure}[ht]
    \centering
    \includegraphics[width=\linewidth]{#1}
    \caption{#2}
    \label{fig:#1}
  \end{figure}%
  % Parser reads alt text from arg #3
}

% \ARJvideo{filename}{caption}{poster image}{transcript file}
% poster image: a still frame displayed before playback (upload separately)
% transcript:   VTT or plain-text transcript asset key (upload separately)
\newcommand{\ARJvideo}[4]{%
  \begin{figure}[ht]
    \centering
    \fbox{\parbox{0.9\linewidth}{%
      \textbf{[Video: #2]}\par
      \smallskip
      \noindent Asset: \texttt{#1} \quad Poster: \texttt{#3}\par
      \noindent Transcript: \texttt{#4}%
    }}
    \caption{#2}
    \label{vid:#1}
  \end{figure}%
}

% \ARJaudio{filename}{caption}{transcript file}
\newcommand{\ARJaudio}[3]{%
  \begin{figure}[ht]
    \centering
    \fbox{\parbox{0.9\linewidth}{%
      \textbf{[Audio: #2]}\par
      \smallskip
      \noindent Asset: \texttt{#1} \quad Transcript: \texttt{#3}%
    }}
    \caption{#2}
    \label{aud:#1}
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
