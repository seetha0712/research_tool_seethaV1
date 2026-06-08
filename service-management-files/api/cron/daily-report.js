// Daily Report Cron Handler
// Runs at 8am IST (2:30 UTC) and 6pm IST (12:30 UTC)
// 1. Starts Render services
// 2. Waits for app to be healthy
// 3. Syncs sources to fetch new articles
// 4. Gets top 25 articles, filters to top 15 unsent
// 5. Sends email report
// 6. Stops services

import { SERVICES, renderApiCall, isConfigured as isRenderConfigured } from '../_utils.js';
import { sendNotification, sendDailyReport, isReportConfigured } from '../_email.js';
import { login, waitForHealthy, syncSources, getArticles, isConfigured as isResearchToolConfigured } from '../_research-tool.js';
import { filterUnsentArticles, markArticlesAsSent } from '../_store.js';

const MAX_ARTICLES_TO_FETCH = 25;
const MAX_ARTICLES_TO_SEND = 15;

async function startServices() {
  const results = [];

  for (const [key, service] of Object.entries(SERVICES)) {
    if (!service.id) continue;

    try {
      console.log(`Starting service: ${service.name}`);
      await renderApiCall(`/services/${service.id}/resume`, 'POST');
      await sendNotification('start', service.name, true);
      results.push({ service: key, success: true });
    } catch (error) {
      console.error(`Failed to start ${service.name}:`, error.message);
      await sendNotification('start', service.name, false, error.message);
      results.push({ service: key, success: false, error: error.message });
    }
  }

  return results;
}

async function stopServices() {
  const results = [];

  for (const [key, service] of Object.entries(SERVICES)) {
    if (!service.id) continue;

    try {
      console.log(`Stopping service: ${service.name}`);
      await renderApiCall(`/services/${service.id}/suspend`, 'POST');
      await sendNotification('stop', service.name, true);
      results.push({ service: key, success: true });
    } catch (error) {
      console.error(`Failed to stop ${service.name}:`, error.message);
      await sendNotification('stop', service.name, false, error.message);
      results.push({ service: key, success: false, error: error.message });
    }
  }

  return results;
}

function getReportType() {
  const now = new Date();
  const istHour = parseInt(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata', hour: 'numeric', hour12: false }));
  return istHour < 12 ? 'morning' : 'evening';
}

export default async function handler(req, res) {
  // Verify this is a cron request (Vercel sets this header)
  const authHeader = req.headers['authorization'];
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    // In development, allow without auth
    if (process.env.NODE_ENV === 'production' && !process.env.ALLOW_UNAUTHENTICATED_CRON) {
      return res.status(401).json({ error: 'Unauthorized' });
    }
  }

  const startTime = Date.now();
  const reportType = getReportType();
  const logs = [];
  const log = (msg) => {
    console.log(msg);
    logs.push(`[${new Date().toISOString()}] ${msg}`);
  };

  log(`Starting daily report cron job (${reportType})`);

  // Check configuration
  if (!isRenderConfigured()) {
    log('ERROR: Render API not configured');
    return res.status(500).json({ error: 'Render API not configured', logs });
  }

  if (!isResearchToolConfigured()) {
    log('ERROR: Research Tool credentials not configured');
    return res.status(500).json({ error: 'Research Tool not configured', logs });
  }

  if (!isReportConfigured()) {
    log('ERROR: Email/Report not configured');
    return res.status(500).json({ error: 'Email not configured', logs });
  }

  try {
    // Step 1: Start services
    log('Step 1: Starting Render services...');
    const startResults = await startServices();
    log(`Services started: ${JSON.stringify(startResults)}`);

    // Step 2: Wait for app to be healthy
    log('Step 2: Waiting for Research Tool to be healthy...');
    await waitForHealthy(180000, 10000); // 3 min max, check every 10s
    log('Research Tool is healthy');

    // Step 3: Login and sync
    log('Step 3: Logging in and syncing sources...');
    const token = await login();
    log('Logged in successfully');

    const syncResult = await syncSources(token, MAX_ARTICLES_TO_FETCH);
    log(`Sync complete: ${JSON.stringify(syncResult)}`);

    // Step 4: Get top articles sorted by relevance score
    log('Step 4: Fetching top articles...');
    const articles = await getArticles(token, {
      limit: MAX_ARTICLES_TO_FETCH,
      sort_by: 'relevance_score',
      sort_order: 'desc'
    });
    log(`Fetched ${articles.length} articles`);

    // Step 5: Filter out already-sent articles
    log('Step 5: Filtering unsent articles...');
    const unsentArticles = await filterUnsentArticles(articles);
    log(`${unsentArticles.length} unsent articles after filtering`);

    // Take top 15
    const topArticles = unsentArticles.slice(0, MAX_ARTICLES_TO_SEND);
    log(`Selected ${topArticles.length} articles for report`);

    // Step 6: Send email report
    if (topArticles.length > 0) {
      log('Step 6: Sending daily report email...');
      const emailSent = await sendDailyReport(topArticles, reportType);

      if (emailSent) {
        log('Email sent successfully');
        // Mark articles as sent
        await markArticlesAsSent(topArticles);
        log('Articles marked as sent');
      } else {
        log('WARNING: Failed to send email');
      }
    } else {
      log('No new articles to send, skipping email');
    }

    // Step 7: Stop services
    log('Step 7: Stopping Render services...');
    const stopResults = await stopServices();
    log(`Services stopped: ${JSON.stringify(stopResults)}`);

    const duration = ((Date.now() - startTime) / 1000).toFixed(1);
    log(`Daily report cron completed in ${duration}s`);

    return res.status(200).json({
      success: true,
      reportType,
      articlesProcessed: articles.length,
      articlesSent: topArticles.length,
      duration: `${duration}s`,
      logs
    });

  } catch (error) {
    log(`ERROR: ${error.message}`);

    // Try to stop services even on error
    try {
      log('Attempting to stop services after error...');
      await stopServices();
    } catch (stopError) {
      log(`Failed to stop services: ${stopError.message}`);
    }

    return res.status(500).json({
      error: error.message,
      logs
    });
  }
}
