# Step 1 application screenshots

Capture the running local app with fictional data after following the project
README's startup/confirmation steps. No application PNGs have been captured by the
agent for this checkpoint: native browser screenshot capture reported
`FrameArrived timed out`, and clicking reported unavailable coordinate geometry.
The sign-in page opened and exposed its controls, but visual review is pending.
Real HTTP checks and automated tests passed; they do not replace these images.

Save screenshots here as:

- `dashboard.png`: signed in as the fictional Prototype Admin, navigation and
  styled Sign out button visible.
- `profile.png`: profile form and navigation visible.
- `settings.png`: settings form and navigation visible.
- `joins_navigation.png`: existing SQL demo page with the updated navigation;
  it may show missing samples in the new local database. Do not seed assessment
  data just for the screenshot. Step 0 will remove this page later.
- `signed_out.png`: sign-in page after clicking Sign out; attempting `/dashboard/`
  afterwards returns to sign-in.

Check desktop and a narrow browser window for wrapping/overlap before capturing.
Use Snipping Tool or a browser capture. Crop to the application so unrelated tabs,
personal information and passwords are absent. Do not photograph source code as
a replacement for a running interface. Add the reviewed PNG files in the student
commit, or a separate evidence commit after review.
