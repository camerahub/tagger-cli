check for config/creds
if none, prompt to create and test

if no args, scan current folder. consider recursive option
elsif load individual frame
or quit if none

foreach found photo:
read exif data, check for camerahub scan tag

if has existing scan
else prompt user to identify the scan
	guess film/frame from filename
	either accept film/frame or just film then prompt frame
	generate scan id

lookup scan id in API
prepare diff of tags
if non-zero diff, ask user to confirm tag write
