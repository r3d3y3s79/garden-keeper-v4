"""
Shared HTML chrome for nurture emails. Matches the styling of auto_reply.py
so the sequence feels like one continuous voice, not 5 different newsletters.
"""

SITE_URL = "https://garden-keeper-v4.vercel.app"


def shell(title: str, body_html: str, subscriber_email: str) -> str:
    """Wrap body content in the standard Garden Keeper email template."""
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title></head>
<body style="margin:0;padding:0;background:#f6f9f4;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#1f2d20;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:32px 16px;">
<table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:14px;overflow:hidden;box-shadow:0 6px 24px rgba(31,45,32,0.08);">
<tr><td style="background:linear-gradient(135deg,#2f6b3a,#74a76a);padding:28px 32px;color:#fff;">
  <div style="font-size:13px;letter-spacing:0.18em;text-transform:uppercase;opacity:0.85;">The Garden Keeper</div>
  <h1 style="margin:8px 0 0;font-size:22px;font-weight:600;line-height:1.3;">{title}</h1>
</td></tr>
<tr><td style="padding:28px 32px;font-size:16px;line-height:1.65;color:#1f2d20;">
  {body_html}
  <p style="margin:28px 0 8px;">— Joe<br><span style="color:#6a7a6b;font-size:14px;">Founder, The Garden Keeper</span></p>
</td></tr>
<tr><td style="background:#f6f9f4;padding:20px 32px;text-align:center;">
  <div style="font-size:12px;color:#6a7a6b;line-height:1.6;">
    You're getting this because you signed up at thegardenkeeper.example.<br>
    <a href="{SITE_URL}/unsubscribe?email={subscriber_email}" style="color:#6a7a6b;">Unsubscribe</a>
  </div>
</td></tr>
</table></td></tr></table>
</body></html>"""
