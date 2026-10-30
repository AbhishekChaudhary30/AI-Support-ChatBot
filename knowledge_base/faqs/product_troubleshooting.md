# Customer Support FAQ: Product Troubleshooting & Technical Issues

> *Notice: These support policies are sample reference data for demonstration purposes.*

## Technical Support & Browser Troubleshooting

### What web browsers and operating systems are officially supported?
Our web application officially supports modern, evergreen browser releases:
- **Google Chrome:** Version 110 and newer.
- **Mozilla Firefox:** Version 110 and newer.
- **Apple Safari:** Version 16 and newer on macOS and iOS.
- **Microsoft Edge:** Version 110 and newer.
Internet Explorer is deprecated and not supported.

### What should I do if the application becomes unresponsive or freezes?
Follow these step-by-step diagnostic actions:
1. **Hard Refresh:** Perform a hard refresh to bypass stale cache files:
   - On Windows: Press `Ctrl + F5` or `Ctrl + Shift + R`.
   - On Mac: Press `Cmd + Shift + R`.
2. **Clear Browser Cache and Cookies:**
   - In Chrome/Edge: Go to **Settings > Privacy and Security > Clear Browsing Data**, select **Cached images and files**, and click **Clear Data**.
3. **Disable Conflicting Extensions:** Ad-blockers or aggressive privacy extensions (e.g. uBlock Origin, Privacy Badger) can occasionally block API requests. Try opening the application in an Incognito / Private window.
4. **Inspect System Status:** Visit our status page at `status.support.example.com` to check for active system incidents or scheduled maintenance.

### What should I do if I see an HTTP 500 or "Server Error" message?
1. Wait 60 seconds and refresh the page, as temporary server spikes usually resolve automatically.
2. If the issue persists, take a screenshot of the error code and copy the request correlation ID displayed at the bottom of the error page.
3. Submit a technical support ticket with the correlation ID, your browser version, and the actions that triggered the error.

### Is there a mobile application available?
Currently, our service provides a fully responsive Progressive Web App (PWA) accessible via mobile Safari and mobile Chrome. You can add the web app to your mobile home screen via the browser's **"Add to Home Screen"** action for a native app experience. Dedicated iOS and Android native apps are scheduled for release later this year.
