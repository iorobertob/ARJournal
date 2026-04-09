\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{arjournal}[2026/04/09 Artistic Research Journal class]

\LoadClass[12pt]{article}

\RequirePackage[utf8]{inputenc}
\RequirePackage[T1]{fontenc}
\RequirePackage{lmodern}
\RequirePackage[a4paper,margin=1in]{geometry}
\RequirePackage{graphicx}
\RequirePackage{xcolor}
\RequirePackage{hyperref}
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

\hypersetup{
  colorlinks=true,
  linkcolor=black,
  urlcolor=blue,
  citecolor=black
}

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

\pagestyle{fancy}
\fancyhf{}
\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0pt}

\titleformat{\section}{\large\bfseries}{\thesection.}{0.5em}{}
\titleformat{\subsection}{\normalsize\bfseries}{\thesubsection.}{0.5em}{}

\newcommand{\makearjtitle}{
  \begin{center}
    {\LARGE \bfseries \@ARJtitle \par}
    \vspace{0.4em}
    {\large \@ARJsubtitle \par}
    \vspace{1em}
    {\normalsize \@ARJauthor \par}
    {\small \@ARJaffiliation \par}
    {\small \@ARJemail \par}
    {\small ORCID: \@ARJORCID \par}
    \vspace{1em}
    {\small Article type: \@ARJarticleType \par}
  \end{center}
  \vspace{1em}
  \noindent\textbf{Abstract.} \@ARJabstract\par
  \vspace{0.5em}
  \noindent\textbf{Keywords.} \@ARJkeywords\par
  \vspace{1em}
}

\newcommand{\ARJfigure}[3]{%
  \begin{figure}[ht]
    \centering
    \includegraphics[width=\linewidth]{#1}
    \caption{#2}
    \label{fig:#1}
  \end{figure}
  % #3 = alt text for parser consumption
}

\newcommand{\ARJvideo}[4]{%
  \begin{figure}[ht]
    \centering
    \fbox{\parbox{0.9\linewidth}{
      \textbf{Video placeholder}\par
      Asset key: \texttt{#1}\par
      Poster image: \texttt{#3}\par
      Transcript asset: \texttt{#4}\par
      \vspace{0.5em}
      #2
    }}
    \caption{#2}
    \label{vid:#1}
  \end{figure}
}

\newcommand{\ARJaudio}[3]{%
  \begin{figure}[ht]
    \centering
    \fbox{\parbox{0.9\linewidth}{
      \textbf{Audio placeholder}\par
      Asset key: \texttt{#1}\par
      Transcript asset: \texttt{#3}\par
      \vspace{0.5em}
      #2
    }}
    \caption{#2}
    \label{aud:#1}
  \end{figure}
}

\newcommand{\ARJembednote}[2]{%
  \begin{quote}
    \textbf{Embedded asset note.} Asset key: \texttt{#1}. #2
  \end{quote}
}

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

\newcommand{\ARJprintdeclarations}{
  \section*{Declarations}
  \noindent\textbf{Funding.} \@ARJfunding\par
  \vspace{0.5em}
  \noindent\textbf{Conflicts of interest.} \@ARJconflicts\par
  \vspace{0.5em}
  \noindent\textbf{License preference.} \@ARJlicense\par
  \vspace{0.5em}
  \noindent\textbf{Acknowledgements.} \@ARJacknowledgements\par
}
