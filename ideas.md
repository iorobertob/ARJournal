- business model. reader has 1 free article a month. others are paid. money goes to authors.  like medium, but peer review. 
- if article is marked as published then it is not shown on options for journal assembly. 


## TODO
- Editorial access required error on production/admin/preview/2/ , page without format/styling		
- Journal should have a publish button. 
- time of the system is wrong, is GMT, we are GMT + 2 + 1 summer time KNOWN
- There should be a button in the Editorial view to mark an article again as not published. 
- The abstract that is written at the upload time is not used for nothign? where is it shown?
- where are the keywords  shown in the published article coming from?
- users should be able to change their email and password. if they change their email they log in with the new email
- there should be an email notification for Editors of a new submission.
- Editorial access required. page needs styling. 
- Journal admin access required. page needs styling. 
- increase width of articles html page, so text takes more space, content tree is pushed to the left and footnotes to the right 
- in the .tex template and cls file it is not contemplated how the authors will reference the images, tables, videos and audio in their manuscript, can you add that to the template, and the explanation. Also, what will happen when authors include \pagebreak or \newpage on their manuscript to control how everything is nicely arranged throught the pages, since the rendered PDF from the journal site will be different?  
- Add Contact, Partners and Editorial Board pages.
- Or simply remove the Contact menu, as there is an email at the footer. change this email. 
- user profiles accessibles by other users. linked from their articles. 
- change html render to be more like the workspace, with smaller font, different background color for the main text and same size of the main text and the side columns for content tree and annotations. the column of anotations should be used for footnotes on the rendered html . 
- create a deploy script 
- check what is used the mailersend config from admin dashboard ofr the info on the .env file?




## UNIT TESTS TO DO:
- Check the flow when more than one reviewers submit reviews
- review is Reject Review works well. 

## BUGS
- when first suggetsing reviewers and substituting the first one, the substitution does not happena and it only deletes the first reviewer
- references to tables is wrong.



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


