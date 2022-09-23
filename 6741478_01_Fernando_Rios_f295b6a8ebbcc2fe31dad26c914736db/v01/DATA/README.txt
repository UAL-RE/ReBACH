---------------------------------------------
# Data for "Which Methods are the Most Effective to Enable Novice Users to Participate in FAIR Ontology Creation? A Usability Study"


Preferred citation (DataCite format):  

  Cui, Hong; Zhang, Limin; Yang, Xingyi (2020): 
  Data for "Which Methods are the Most Effective to Enable Novice Users to Participate in FAIR Ontology Creation? A Usability Study". 
  University of Arizona Research Data Repository. 
  Dataset. https://doi.org/10.25422/azu.data.12616004


Corresponding Author:   
  Hong Cui, School of Information/University of Arizona, hong1.cui@gmail.com


License:
  CC0


DOI:
  azu.data.12616004



---------------------------------------------
## Summary

A usability test experiment was employed to evaluate the efficiency, effectiveness 
and user satisfaction with a set of four "add2ontology" user interfaces (UIs)
that allow an end user to add terms and their relations to an ontology. 
The experiment consisted of a pre-experiment session, and two activity sessions.
In the pre-experiment session,  33 participants  remotely filled out a pre-experiment 
survey consisting of four questions regarding their experience with controlled 
vocabulary editors and wikis. After completing the pre-experiment questionnaire, 
participants were scheduled to watch a 3-6 minute video tutorial for each method. 
After watching each video, participants completed a web-based questionnaire consisting
of five questions(session 1). In the second session, participants  watched the videos again 
and completed a hands-on task using each of the four methods  to add new terms and 
properties to the CAREX Ontology. After finishing the task, participants  responded to 
the same questionnaire as in the first session.  

The questionare responses data were collected from the three-round surveys. The logs data from
the four UIs after finishing the task were clollected. The Friedman rank sum test, 
Wilcoxon signed-rank test, Cochran's Q test, and Spearman correlation coefficient analysis 
were performed to compare the usability among the four tools and  the change before 
and after completing the hands-on task



---------------------------------------------
## Files and Folders


#### Questionaire Response Data folder: Three-round survey data. 
- Pre-experiment Questionnaire_response.csv: Questions regarding participants' experience 
with controlled vocabulary editors and wikis. This data was used to evaluate the association 
between previous experience with user satisfaction.
- Session 1 Questionnaire_response.csv: Questions regarding participants' percerptions 
with the four methods after wacthing the video tutorials. This data was used to analyze the user 
satisfaction after wacthing the video tutorials.
- Session 2 Questionnaire_response.csv: Questions regarding participants' percerptions 
with the four methods after completing the hands-on task. This data was used to analyze the user 
satisfaction change after doing task.

#### Experiment data folder: The data generated during participants doing the task
- User logs_raw_history: the raw user logs from the four UIs, including the history
users did the task. This data was used to analyze the effictiveness of the four UIs.
- User logs_raw_time: the raw user logs from the four UIs, mainly about the time participants
started and completed the task. This data was used to analyze the efficiency of the four UIs.
- User logs_processed: the structured data of processed user logs(the two raw user logs) for 
each UIs, including the task completion and time.



---------------------------------------------
## Materials & Methods

- Notepad++, https://notepad-plus-plus.org/downloads/. used to open the raw user logs(OWL file).

