# Release notes

These release notes comprise information about  improvements made in release
0.7.0 beta and in the  current release 0.8.0 beta. In the beta 0.7.0 release
the following improvements were made.

## 0.7.0

0.7.0 Beta was released [xxxx] the following release note includes the
improvements that were made during that release.

### Issue 46: Add METS XML download link to AIP detail page

This addition adds a download button on the AIP detail page that allows users
to download the AIP’s METS  file so they can review it.

### Issue 66: Add default 404 error page

Previously, navigating to an unhandled application path would result in a
barebones “not found” error  page that wouldn’t include the application’s
navigation bar and styling. Added a more usable and visually consistent 404
error page.

### Issue 91: When deleting a storage service, remove agents associated with it

If a storage service is removed from AIPscan, then related agent information
will now be removed from  AIPscan’s database.

### Issue 99: Update AIPscan database with deleted storage service AIPs

Previously, if an AIP was deleted from the storage service this was not
reflected in AIPscan’s database  and the deleted AIP would continue to be shown
on the UI. This fix addresses this issue and any AIPs deleted in the storage
service will now be removed from the AIPscan database and will no longer appear
in the UI.

### Issue 180: Display PREMIS object XML, if populated, when viewing files

This piece of work now allows users to see characterization tool output in its
XML form within AIPscan.

## 0.8.0

This next section contains release notes related to the most recent update to
AIPscan

### Issue 13: Show active tab in main menu

This is an ease of use feature that visually highlights, in the navigation bar,
which section a user is currently working in. For example, if a user is on the
detail page for a storage service then “Archivematica Storage Services” is
highlighted, shown with white text rather than gray, in the navigation bar.

### Issue 23: window.location.origin paths will not work on sites where AIPscan is not hosted at root url

The window.location.origin values were used in Javascript URL generation for
the _reporter/reports/_ and _reporter/view_aips pages_. The URLs generated
would fail if AIPscan was being hosted at subpaths of a root url, e.g.
_example.com/dir/AIPscan/_ instead of _example.com/AIPscan_. This issue has
been fixed and will allow for AIPscan to be hosted at subpaths of a root URL.

### Issue 77: Add GUI element to largest files report to control number of files shown

Previously, the largest AIPs and largest files reports would, by default, show
only up to five results. The only way to alter this was to manually alter
report URL parameters. This fix adds a web UI input component that lets users
change the number of results shown more easily and obviously.

### Issue 149: Problem: CSV exports are not sortable by size column

Some CSV exports have human-readable size columns, but the values in these
aren’t easy to use for sorting purposes. These CSV exports will now also
include an additional size column where the size is expressed simply as a
number of bytes, a more easily sortable value.

### Issue 209: PROBLEM: AIPs page loading slowly

Previously, results paging on the AIPs page was being handled client-side, by
the web browser using Javascript. This required data for every AIP (matching
the currently selected storage service and location criteria) to be retrieved
from the database and included in the web page’s HTML. This made AIPs page
potentially take a long time to load in web browsers.

### Issue 216: AIP page doesn’t use server-side paging

Previously, results paging on the AIP detail page, of an AIP’s files, was being
handled client-side, by the web browser using Javascript. AIPscan now uses
server-side results paging on the AIP detail page. Given that results paging on
the AIPs page only displays up to 10 AIPs at a time the application now only
sends data for these specific AIPs rather than all AIPs. This makes the AIP
page load much faster in web browsers when a lot of AIPs exist in AIPscan’s
database.

### Issue 217: Create a script to generate test content for AIPscan testing

A CLI tool was added to allow developers to generate sample database content to
make it easier to do performance testing and development in general.

### Issue 234: When the database is unpopulated the AIPs and Reports pages will result in “Internal Server Error”

Previous versions of AIPscan had a silent failure when the database was
unpopulated and so users were unaware that the database was unpopulated. This
fix alerts users to the fact that information is either not being pulled from
the storage space or that other potential issues are preventing AIPscan from
capturing and displaying information.

### Issue 241: Add lock file functionality to fetch tool

A CLI option was added to the CLI fetch tool to enable use of a lockfile. Usage
of this option makes it easier to use a lockfile to avoid accidental,
overlapping runs of the fetch tool (if scheduled to run automatically via cron,
for example).
