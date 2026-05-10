- business model. reader has 1 free article a month. others are paid. money goes to authors.  like medium, but peer review. 
- lmta vsi can establish a uab?
- if article is marked as published then it is not shown on options for journal assembly. 


## TODO
- Editorial access required error on production/admin/preview/2/ , page without format/styling
- when uploading files it says 0KB for all files, are they really being updated?
- When removing or accepting reviewers, the page should not reload and the page cards should be updated. no ajax used. 
- When refreshing suggestions for reviewers, the already approved reviewers should not be refreshed, they should remain in the cards. no ajax
- Replace Reviewer modal is shown on the corner of the page, it should be styled properly. 
- url of the invitation email is hardcoded, this should be corrected.	
- invitation takes to an url that is shown to user before they log in. they should be prompted to login if they are not, or if the invitation belongs to another account then be informed of such and invite to log out. 
- several useers seem to be able to be logged in from the saem computer, this is wrong. explain why is this a security concern or not?
- aedia files are not rendereed in the review workspace, nor are they in the html. something is wrong. 	
- Journal should have a publish button. 
- time of the system is wrong, is GMT, we are GMT + 2 + 1 summer time now
- section tree in html view shoul be collapsable.
- Available Articles (Accepted / In Production) section is not showing all published or accepted articles. 
- There should be a button in the Editorial view to mark an article again as not published. 
- when articles are added from Available Articles to Articles in This Issued, the card that appears on ARticles in This Issue shoul immediatly have already the dropdown menu to select the section it will be in. 
- The abstract that is written at the upload time is not used for nothign? where is it shown?
- where are the keywords shown in the published article coming from?
- users should be able to change their email and password. if they change their email they log in with the new email
- there should be an email notification for Editors of a new submission.
- Editorial access required. page needs styling. 
- Journal admin access required. page needs styling. 
- increase width of articles html page, so text takes more space, content tree is pushed to the left and footnotes to the right
- in the .tex template and cls file it is not contemplated how the authors will reference the images, tables, videos and audio in their manuscript, can you add that to the template, and the explanation. Also, what will happen when authors include \pagebreak or \newpage on their manuscript to control how everything is nicely arranged throught the pages, since the rendered PDF from the journal site will be different?  
- Review notification badges behaviour, if they are mark as read, or one by one or in bulk, etc. 
- Add Contact, Partners and Editorial Board pages.
- Or simply remove the Contact menu, as there is an email at the footer. change this email. 

## BUGS
- When Returning the article to author from the Desk check, the author should be notified and the submission in his submissions list should allow him to to to a resubmit flow/interface



- Reconsider name
- celebration at IB 
- 



## KNOWN ISSUES
-  Why not truly embedded/playable: WeasyPrint is a CSS print renderer — it produces static PDFs with no concept of embedded media. Truly playable PDFs require PDF RichMedia annotations (PDF 2.0) which only work in Adobe Acrobat and require post-processing the binary PDF with a low-level library like pikepdf. Even then, macOS Preview, browsers, and most PDF readers don't support inline media playback. The clickable link approach works in every viewer. 


## MANUSCRIPT LIFECYCLE
  The full status lifecycle

  draft → submitted → desk_review → reviewer_suggestion
       → under_review → revision_requested
                             ↓ (author resubmits)                               
                           revised  ← current state
                             ↓ (re-reviewed, accepted)                          
                          accepted → in_production      
                             ↓ (editor publishes article)                       
                          published  ← what HTMLBuild implies   


