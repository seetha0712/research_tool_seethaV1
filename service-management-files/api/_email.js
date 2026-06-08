import nodemailer from 'nodemailer';

const SMTP_HOST = process.env.SMTP_HOST || 'smtp.gmail.com';
const SMTP_PORT = parseInt(process.env.SMTP_PORT || '587', 10);
const SMTP_USER = process.env.SMTP_USER;
const SMTP_PASSWORD = process.env.SMTP_PASSWORD;
const ADMIN_EMAILS = (process.env.ADMIN_NOTIFICATION_EMAILS || '')
  .split(',')
  .map(e => e.trim())
  .filter(Boolean);

// Report recipients (can be different from admin notifications)
const REPORT_EMAILS = (process.env.REPORT_EMAILS || process.env.ADMIN_NOTIFICATION_EMAILS || '')
  .split(',')
  .map(e => e.trim())
  .filter(Boolean);

function getTransporter() {
  return nodemailer.createTransport({
    host: SMTP_HOST,
    port: SMTP_PORT,
    secure: SMTP_PORT === 465,
    auth: {
      user: SMTP_USER,
      pass: SMTP_PASSWORD
    }
  });
}

function isEmailConfigured() {
  return !!(SMTP_USER && SMTP_PASSWORD && ADMIN_EMAILS.length > 0);
}

export async function sendNotification(action, serviceName, success, errorMessage = null) {
  if (!isEmailConfigured()) {
    console.log('Email not configured, skipping notification');
    return false;
  }

  const transporter = getTransporter();

  const timestamp = new Date().toISOString();
  const actionPast = action === 'start' ? 'started' : 'stopped';
  const actionVerb = action === 'start' ? 'Starting' : 'Stopping';

  const subject = success
    ? `[Research Tool] Service ${actionPast}: ${serviceName}`
    : `[Research Tool] FAILED to ${action} service: ${serviceName}`;

  const statusColor = success
    ? (action === 'start' ? '#28a745' : '#dc3545')
    : '#dc3545';

  const statusText = success ? `Successfully ${actionPast}` : `Failed to ${action}`;

  const html = `
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #1a73e8; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .status { display: inline-block; padding: 8px 16px; background-color: ${statusColor}; color: white; border-radius: 4px; font-weight: bold; }
        .details { margin-top: 20px; }
        .details table { width: 100%; border-collapse: collapse; }
        .details td { padding: 8px; border-bottom: 1px solid #ddd; }
        .details td:first-child { font-weight: bold; width: 140px; }
        .footer { margin-top: 20px; font-size: 12px; color: #666; text-align: center; }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h2>Infrastructure Notification</h2>
        </div>
        <div class="content">
          <p><span class="status">${statusText}</span></p>
          <div class="details">
            <table>
              <tr><td>Action:</td><td>${actionVerb} Service</td></tr>
              <tr><td>Service:</td><td>${serviceName}</td></tr>
              <tr><td>Timestamp:</td><td>${timestamp}</td></tr>
              ${errorMessage ? `<tr><td>Error:</td><td style="color: #dc3545;">${errorMessage}</td></tr>` : ''}
            </table>
          </div>
        </div>
        <div class="footer">
          <p>This is an automated notification from Research Tool Infrastructure Manager.</p>
        </div>
      </div>
    </body>
    </html>
  `;

  try {
    await transporter.sendMail({
      from: SMTP_USER,
      to: ADMIN_EMAILS.join(', '),
      subject,
      html
    });
    console.log(`Notification sent to ${ADMIN_EMAILS.join(', ')}`);
    return true;
  } catch (error) {
    console.error('Failed to send email notification:', error);
    return false;
  }
}

export async function sendDailyReport(articles, reportType = 'morning') {
  if (!isEmailConfigured() || REPORT_EMAILS.length === 0) {
    console.log('Email not configured for reports, skipping');
    return false;
  }

  const transporter = getTransporter();
  const timestamp = new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' });
  const reportTitle = reportType === 'morning' ? 'Morning' : 'Evening';

  const subject = `[GenAI Research] ${reportTitle} Digest - ${new Date().toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata' })} (${articles.length} articles)`;

  const articleRows = articles.map((article, index) => {
    const score = article.relevance_score || article.score || 'N/A';
    const category = article.category || 'Uncategorized';
    const summary = article.summary || article.description || 'No summary available';
    const truncatedSummary = summary.length > 300 ? summary.substring(0, 300) + '...' : summary;

    return `
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 16px; vertical-align: top;">
          <div style="font-weight: bold; color: #1a73e8; margin-bottom: 8px;">
            ${index + 1}. <a href="${article.link || '#'}" style="color: #1a73e8; text-decoration: none;">${article.title || 'Untitled'}</a>
          </div>
          <div style="display: flex; gap: 12px; margin-bottom: 8px; font-size: 12px;">
            <span style="background: #e8f0fe; color: #1a73e8; padding: 2px 8px; border-radius: 4px;">Score: ${score}</span>
            <span style="background: #f3e8ff; color: #7c3aed; padding: 2px 8px; border-radius: 4px;">${category}</span>
            ${article.source_name ? `<span style="background: #fef3c7; color: #d97706; padding: 2px 8px; border-radius: 4px;">${article.source_name}</span>` : ''}
          </div>
          <div style="color: #555; font-size: 14px; line-height: 1.5;">
            ${truncatedSummary}
          </div>
        </td>
      </tr>
    `;
  }).join('');

  const html = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background: #f5f5f5; }
        .container { max-width: 700px; margin: 0 auto; background: white; }
        .header { background: linear-gradient(135deg, #1a73e8, #4285f4); color: white; padding: 30px; text-align: center; }
        .header h1 { margin: 0 0 8px 0; font-size: 24px; }
        .header p { margin: 0; opacity: 0.9; font-size: 14px; }
        .stats { display: flex; justify-content: center; gap: 30px; padding: 20px; background: #f8fafc; border-bottom: 1px solid #eee; }
        .stat { text-align: center; }
        .stat-value { font-size: 28px; font-weight: bold; color: #1a73e8; }
        .stat-label { font-size: 12px; color: #666; text-transform: uppercase; }
        .content { padding: 0; }
        .articles-table { width: 100%; border-collapse: collapse; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #888; background: #f8fafc; }
        .footer a { color: #1a73e8; }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>GenAI Research ${reportTitle} Digest</h1>
          <p>Top articles curated for you | ${timestamp}</p>
        </div>
        <div class="stats">
          <div class="stat">
            <div class="stat-value">${articles.length}</div>
            <div class="stat-label">Articles</div>
          </div>
          <div class="stat">
            <div class="stat-value">${articles.filter(a => (a.relevance_score || a.score || 0) >= 8).length}</div>
            <div class="stat-label">High Score (8+)</div>
          </div>
        </div>
        <div class="content">
          <table class="articles-table">
            <tbody>
              ${articleRows}
            </tbody>
          </table>
        </div>
        <div class="footer">
          <p>This is an automated daily digest from the GenAI Research Tool.</p>
          <p>Articles are ranked by AI relevance scoring.</p>
        </div>
      </div>
    </body>
    </html>
  `;

  try {
    await transporter.sendMail({
      from: SMTP_USER,
      to: REPORT_EMAILS.join(', '),
      subject,
      html
    });
    console.log(`Daily report sent to ${REPORT_EMAILS.join(', ')} with ${articles.length} articles`);
    return true;
  } catch (error) {
    console.error('Failed to send daily report:', error);
    return false;
  }
}

export function isReportConfigured() {
  return isEmailConfigured() && REPORT_EMAILS.length > 0;
}
