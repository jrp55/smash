Snail Mail Archival and Search Helper
-------------------------------------

A hackathon project using HPE [Haven OnDemand](https://www.havenondemand.com/).

1. Take a picture of your snail mail
2. Upload the picture
3. Search your mail

### Requirements
* Python 2.7
  * [requests](http://docs.python-requests.org/en/latest/)
  * [Flask](http://flask.pocoo.org/)
* A [Haven OnDemand](https://www.havenondemand.com/) API key

### Running
It's not very user friendly yet. Adjust app.py to point at your HoD API key and run the script. Use a web browser to access the website created.

### Public Service Announcement
When using this, your photo is sent to the 'cloud' (HPE's Haven OnDemand) for OCR processing, and the extracted text is stored in it. Obviously, your photos and your mail are likely to contain personal and sensitive material, so be aware of what you upload!
