import nodemailer from 'nodemailer';

const SMTP_HOST = process.env.SMTP_HOST || 'smtp.gmail.com';
const SMTP_PORT = parseInt(process.env.SMTP_PORT || '587', 10);
const SMTP_USER = process.env.SMTP_USER;
const SMTP_PASSWORD = process.env.SMTP_PASSWORD;
const ADMIN_EMAILS = (process.env.ADMIN_NOTIFICATION_EMAILS || '')
  .split(',')
  .map(e => e.trim())
  .filter(Boolean);

function isEmailConfigured() {
  return !!(SMTP_USER && SMTP_PASSWORD && ADMIN_EMAILS.length > 0);
}

export async function sendNotification(action, serviceName, success, errorMessage = null) {
  if (!isEmailConfigured()) {
    console.log('Email not configured, skipping notification');
    return false;
  }

  const transporter = nodemailer.createTransport({
    host: SMTP_HOST,
    port: SMTP_PORT,
    secure: SMTP_PORT === 465,
    auth: {
      user: SMTP_USER,
      pass: SMTP_PASSWORD
    }
  });

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
