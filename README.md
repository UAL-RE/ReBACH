# DataRepository_backup
Python-based tool to enable data preservation of UA Data Repository to a
cloud-hosted storage solution

Package will include:
1. API data retrieval from Figshare instance using this
   [Python](https://github.com/ualibraries/figshare) package
2. Processing data for preservation using BagIt. The Library of Congress
   [Python Bagit](https://github.com/LibraryOfCongress/bagit-python)
   comes to mind.
3. OAI-PMH harvesting may be needed. [Figshare implements OAI-PMH v2](https://docs.figshare.com/#oai_pmh).
   This [Python OAI-PMH package](https://github.com/bloomonkey/oai-harvest)
   for harvesting records may be useful as it is stated to work with Figshare
