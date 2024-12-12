Python free threat feed


GUI app is under development:

## Usage

You can run the basic cli based feed by running 

`python3 feed.py`

The GUI app is available by installing requirements in a venv

`python3 -m venv feed`

`source feed/bin/activate`

`pip install -r requirements.txt`

Then you can run the feed by running

`python3 app.py`

# features

- This threat feed displays URLhaus data in a scrolling fashion.

- You can search for threats using ID# or keywords

- Basic metrics: top 5 URL, top 5 reporters, top 5 tags



# Issues:

Sources - 
- Adding sources is not working at this time

- currently the labels are hardcoded, i have been trying to get them to be dynamically generated but i have not been able to do it (when source is hardcoded such as OTX, URLHaus)

- when adding sources it does not seem to even load that source.

Pause and resume - 

- You can pause but you cant resume where you left off


# future plans

- I'd like to have a more robust and customizable metrics page
  
- I'd also like to fix these issues

- I'd like to make a feature with UFW block. Where you click it and a shell script automatically creates rules to block the top 5 URLs for 90 days


# You can help!

I'd would like somebody to help me out in fixing these issues, especially the dynamic generation of data.(stack overflow always does not help most of the time and make stupid comments)

Reach out to me at dereksamjohnston@gmail.com if you would like to offer assistance in making this better and actually be useful
