# The HtmlTemplate Class

For comparing one web state to another, Demodocus makes use of the 
![HtmlTemplate class](../demodocusfw/web/template.py), implemented specifically
for detecting significant changes between DOMs. HtmlTemplate allows for content that changes on
a page over time or across page loads. We call this *unstable* content. Unstable content gets marked up
in the HtmlTemplate's _full_tree so we can keep track of it.

HtmlTemplate supports three main functions:
- **ADD**: Adds an html document to the template. The html is combined with any html that has been added
    to the template already. Content that is different in the new html is marked as unstable. All html added
    to a template is assumed to be different variations of the same page.
- **MATCH**: Matches an html document to the template. Content marked as unstable in the template is allowed to be
    different. Content that is not marked as unstable must match. 
    Between two elements:
    - each attribute must exist and have the same value (not necessarily in the same order)
    - the text value if there is one must match, 
    - the child elements must recursively match (not necessarily in the same order)
- **UPDATE**: This is meant to be called when some part of the html has changed; for example, if the url has not
    changed but we know something on the page has changed. When we update the tree, all unstable content is
    kept as unstable, but other content is updated to the new html. The purpose is to quickly create a template
    that is appropriate to the new content.

## Examples
Example of ADD and UPDATE functions:
```html
<div demod_reachable="true" class="usajobs-event__date start">
	<span>Jul 23</span>
</div>

-- ADD the following:

<div demod_reachable="true" class="usajobs-event__date start">
	<span>Jun 8</span>
</div>

--> RESULT:  The span's text is marked as unstable. Both values are included.

<div demod_reachable="true" class="usajobs-event__date start">
	<span unstable_text="true">Jul 23||Jun 8</span>
</div>

-- UPDATE with the following:

<div demod_reachable="false" class="usajobs-event__date start">
	<span>Aug 15</span>
</div>

--> RESULT: The span's text remains unstable, but the demod_reachable attribute is updated.

<div demod_reachable="false" class="usajobs-event__date start">
	<span unstable_text="true">Jul 23||Jun 8||Aug 15</span>
</div>

-- MATCH the following:

<div demod_reachable="false" class="usajobs-event__date start">
	<span>Sep 9</span>
</div>

--> RESULT: TRUE. Since the span's text is marked unstable it will match anything.
```

Real-world examples

usajobs.gov gives result:
```
2020-06-02 15:05:26,474 crawler.webaccess:205 INFO https://www.usajobs.gov took 2 seconds to stabilize.
(Load 4 more times...)
2020-06-02 15:05:26,517 crawler.webaccess:212 INFO Found unstable content /html/body/main/div[4]/div/ul/li[2]/div[1]/div/div[2]/span
2020-06-02 15:05:26,517 crawler.webaccess:212 INFO Found unstable content /html/body/main/div[4]/div/ul/li[2]/div[2]/p/a[2]
2020-06-02 15:05:26,517 crawler.webaccess:212 INFO Found unstable content /html/body/main/div[4]/div/ul/li[2]/div[2]/p/a[1]
2020-06-02 15:05:26,517 crawler.webaccess:212 INFO Found unstable content /html/body/main/div[4]/div/ul/li[2]/div[2]/h3/a
2020-06-02 15:05:26,517 crawler.webaccess:212 INFO Found unstable content /html/body/main/div[4]/div/ul/li[1]/div[2]/h3/a
2020-06-02 15:05:26,517 crawler.webaccess:212 INFO Found unstable content /html/body/main/div[4]/div/ul/li[2]/div[2]/h3/span
2020-06-02 15:05:26,517 crawler.webaccess:212 INFO Found unstable content /html/body/main/div[4]/div/ul/li[1]/div[1]/div/div[2]/span
2020-06-02 15:05:26,518 crawler.webaccess:212 INFO Found unstable content /html/body/main/div[4]/div/ul/li[1]/div[2]/p/a[2]
2020-06-02 15:05:26,518 crawler.webaccess:212 INFO Found unstable content /html/body/main/div[4]/div/ul/li[1]/div[2]/p/a[1]
```
A relevant portion of the template showing calendar content that varies across page loads:
```html
<li demod_reachable="true" class="usajobs-landing-events__item">
	<div demod_reachable="true" class="usajobs-event--card__calendar">
		<div demod_reachable="true" class="usajobs-event__calendar-container">
			<span class="usajobs-event--card__year" demod_reachable="true">                        2020                    </span>
			<div demod_reachable="true" class="usajobs-event__date start">
				<span itemprop="startDate" demod_reachable="true" content="2016-09-13T09:00 -0400" unstable_text="true">                            Jul 23                        ||                            Jun 10                        ||                            Jun 30                        ||                            Aug 5                        </span>
			</div>
		</div>
	</div>
	<div demod_reachable="true" class="usajobs-event--card__body">
		<h3 demod_reachable="true" class="usajobs-event--card__item-title">
			<a href="/Notification/Events/#OM000357||/Notification/Events/#OM000356||/Notification/Events/#OM000338||/Notification/Events/#OM000374" demod_reachable="true" class="usajobs-event--card__item-title" unstable_attributes="href" unstable_text="true">Navigating USAJOBS - Finding and Applying for Federal Jobs||Writing Your Federal Resume</a>
			<span class="usajobs-event--card__im" demod_reachable="true">                        Virtual                    </span>
		</h3>
		<p demod_reachable="true" class="usajobs-event--card__text">                    Hosted by <a target="_blank" demod_reachable="true" href="" unstable_text="true">Office of Personnel Managment||Office of Personnel Management<span class="sr-only" demod_reachable="false">Opens in a new window</span>
			</a>
			<a href="/Notification/Events/#OM000357||/Notification/Events/#OM000356||/Notification/Events/#OM000338||/Notification/Events/#OM000374" demod_reachable="true" class="usajobs-event--card__more-info" unstable_attributes="href">More information</a>
		</p>
	</div>
</li>
```

time.gov gives result:
```
2020-06-02 14:57:13,962 crawler.webaccess:207 WARNING https://www.time.gov loaded in 2 seconds except for unstable xpaths: {'/html/body/div[1]/div[3]/div/div[3]/span[1]'}
(Load 4 more times...)
2020-06-02 14:57:13,965 crawler.webaccess:212 INFO Found unstable content /html/body/div[1]/div[3]/div/div[3]/span[2]
2020-06-02 14:57:13,965 crawler.webaccess:212 INFO Found unstable content /html/body/div[1]/div[3]/div/div[3]/span[1]
```
and relevant portion of the template showing content that changes with time and across page loads:
```html
<span id="myTime" demod_reachable="true" unstable_text="true">12:13:57 P.M.||12:14:21 P.M.||12:14:43 P.M.||12:15:04 P.M.||12:15:06 P.M.||12:14:19 P.M.||12:13:59 P.M.||12:15:28 P.M.||12:14:41 P.M.||12:15:26 P.M.</span>
<br demod_reachable="false"/>
<br demod_reachable="false"/>Your clock is off by: <br demod_reachable="false"/>
<span id="realTimeDif" demod_reachable="true" unstable_text="true">+0.009||+0.024||+0.007||+0.006||+0.038</span>						
```

## Asynchronous and changing content
The HtmlTemplate class is used to identify content on a webpage that changes over time
or from load to load.

When the web crawler first loads a page, it loads the page multiple times to see if any
content changes from load to load. In addition, for each load the crawler waits to see 
if the content on the page changes over time.
The crawler takes all of these content changes and adds them to a template representing
the state. Ideally the final template will be able to match any mutation of the 
state's changing content (but will not match any changes resulting from user interaction).

### Configuration
The following three configuration variables apply to the detection of changing content:
```python
# To check for changing and delayed content. We load the page multiple times and
#   wait at least THRESHOLD and at most TIMEOUT seconds to see if any content is changing.
PAGE_CHANGE_NUM_LOADS = 10  # Load the page this many times to see if any content changes.
PAGE_CHANGE_THRESHOLD = 8  # Wait at least this long to see if content is still changing.
PAGE_CHANGE_TIMEOUT = 20  # Don't wait any longer than this.
```