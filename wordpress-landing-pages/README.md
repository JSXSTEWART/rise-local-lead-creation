# WordPress Dynamic Landing Pages
## Stripped-Down WordPress Installation for Rise Local Lead Generation

This directory contains a **minimal WordPress installation** with a custom theme for generating dynamic, category-specific landing pages.

---

## WHAT THIS IS

A lightweight WordPress system that:
- Generates dynamic landing pages for each business category (electricians, plumbers, HVAC, etc.)
- Pulls lead data from **Supabase** database
- Creates custom URLs like `/electricians/`, `/plumbers/`, `/hvac/`
- Handles form submissions and sends data back to Supabase
- Integrates with the Rise Local pipeline

---

## ARCHITECTURE

```
WordPress (MySQL)          Supabase (PostgreSQL)
       ↓                          ↓
Content Management          Lead Data Storage
- Page templates            - Qualified leads
- Form settings             - Business data
- SEO metadata              - Contact info
       ↓                          ↓
       └──────── PHP ─────────────┘
                  ↓
          Landing Pages:
          - /electricians/
          - /plumbers/
          - /hvac/
          - /business/{name}/
```

**Dual Database System:**
- **WordPress MySQL** - For WordPress content management only
- **Supabase PostgreSQL** - For all lead data (same database used by Rise pipeline)

---

## INSTALLATION

### Prerequisites

1. **Web Server:** Apache or Nginx with PHP 7.4+
2. **PHP:** 7.4+ with extensions: mysqli, curl, json, mbstring
3. **MySQL:** 5.7+ or MariaDB 10.2+
4. **Supabase Account:** Active project with leads table

### Step 1: Download WordPress

```bash
cd /home/user/rise-local-lead-creation/wordpress-landing-pages

# Download latest WordPress
wget https://wordpress.org/latest.tar.gz
tar -xzf latest.tar.gz --strip-components=1
rm latest.tar.gz
```

### Step 2: Create MySQL Database

```bash
mysql -u root -p
```

```sql
CREATE DATABASE rise_landing_pages CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'wp_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON rise_landing_pages.* TO 'wp_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Step 3: Configure WordPress

```bash
# Copy sample config
cp wp-config-sample.php wp-config.php

# Edit wp-config.php
nano wp-config.php
```

**Add these configurations:**

```php
// Database settings
define('DB_NAME', 'rise_landing_pages');
define('DB_USER', 'wp_user');
define('DB_PASSWORD', 'your_secure_password');
define('DB_HOST', 'localhost');

// Supabase settings (for lead data)
define('SUPABASE_URL', 'https://jitawzicdwgbhatvjblh.supabase.co');
define('SUPABASE_KEY', 'your-supabase-service-key');

// Security keys - generate at https://api.wordpress.org/secret-key/1.1/salt/
// Paste generated keys here

// Performance & security
define('DISALLOW_FILE_EDIT', true);
define('DISALLOW_FILE_MODS', true);
define('WP_POST_REVISIONS', false);
define('AUTOSAVE_INTERVAL', 300);
define('WP_AUTO_UPDATE_CORE', false);
```

### Step 4: Set Permissions

```bash
# Set ownership (replace www-data with your web server user)
sudo chown -R www-data:www-data /path/to/wordpress-landing-pages

# Set directory permissions
find . -type d -exec chmod 755 {} \;

# Set file permissions
find . -type f -exec chmod 644 {} \;
```

### Step 5: Complete WordPress Installation

1. Visit: `http://your-domain.com/wp-admin/install.php`
2. Follow the 5-minute installation:
   - Site Title: "Rise Local Lead Generation"
   - Username: (your admin username)
   - Password: (strong password)
   - Email: (your email)
3. Click "Install WordPress"

### Step 6: Activate Theme

1. Login to WordPress admin: `http://your-domain.com/wp-admin/`
2. Go to **Appearance → Themes**
3. Activate **"Rise Landing Pages"** theme
4. Go to **Settings → Permalinks**
5. Select **"Post name"** structure
6. Click **"Save Changes"** (this activates custom rewrite rules)

### Step 7: Test Installation

Visit these URLs to test:
- `http://your-domain.com/` - Should show category index
- `http://your-domain.com/electricians/` - Should show electricians landing page
- `http://your-domain.com/plumbers/` - Should show plumbers page (if template created)

---

## THEME STRUCTURE

```
wp-content/themes/rise-landing/
├── style.css                      # Main stylesheet with theme metadata
├── functions.php                  # Theme setup and custom functions
├── index.php                      # Default template (category index)
│
├── includes/
│   ├── supabase-client.php        # Supabase API integration
│   ├── form-handler.php           # Form submission handler
│   └── dynamic-content.php        # Dynamic content generators
│
├── page-templates/
│   ├── category-electricians.php  # Electricians landing page
│   ├── category-plumbers.php      # Plumbers landing page (create this)
│   ├── category-hvac.php          # HVAC landing page (create this)
│   ├── category-contractors.php   # Contractors page (create this)
│   └── single-business.php        # Single business page (optional)
│
└── assets/
    ├── css/                       # Additional CSS (optional)
    ├── js/
    │   └── main.js                # JavaScript for form handling
    └── images/                    # Theme images (optional)
```

---

## CREATING NEW CATEGORY PAGES

To add a new category (e.g., plumbers):

### 1. Copy Electricians Template

```bash
cd wp-content/themes/rise-landing/page-templates/
cp category-electricians.php category-plumbers.php
```

### 2. Edit Template

```php
// Change category variable
$category = 'plumber';  // Changed from 'electrician'

// Update page title
$page_title = "Find Licensed Plumbers in Texas";

// Update icon
<?php echo rise_get_category_icon('plumbers'); ?>
```

### 3. Register Template in functions.php

Already registered! Check line ~65 in `functions.php`:

```php
$templates['page-templates/category-plumbers.php'] = 'Plumbers Landing Page';
```

### 4. Flush Rewrite Rules

Go to WordPress admin → **Settings → Permalinks** → Click **"Save Changes"**

### 5. Test New Page

Visit: `http://your-domain.com/plumbers/`

---

## CUSTOMIZATION

### Change Colors

Edit `style.css` around line 100:

```css
/* Current gradient */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* Change to your brand colors */
background: linear-gradient(135deg, #your-color-1 0%, #your-color-2 100%);
```

### Add Custom Pain Points

Edit `includes/dynamic-content.php` → `rise_get_category_pain_points()` function

### Modify Form Fields

Edit page templates → Find `<form id="lead-form">` section → Add/remove fields

### Change Email Notifications

Edit `includes/form-handler.php` → `rise_send_admin_notification()` function

---

## INTEGRATION WITH RISE PIPELINE

### Data Flow

```
1. User visits /electricians/
   ↓
2. WordPress pulls qualified electricians from Supabase
   ↓
3. User submits form
   ↓
4. WordPress creates new lead in Supabase (status: 'new')
   ↓
5. Rise pipeline picks up lead for processing
   ↓
6. Lead goes through pre-qualification → enrichment → outreach
```

### Database Connection

WordPress connects to **same Supabase database** used by Rise pipeline:
- Reads from `leads` table (status='qualified')
- Writes to `leads` table (status='new', source='landing_page')

### No Data Duplication

Since both systems use the same database, there's no sync needed!

---

## URL STRUCTURE

### Category Pages
- `/electricians/` - All electricians in Texas
- `/electricians/austin/` - Electricians in Austin
- `/plumbers/` - All plumbers
- `/hvac/` - All HVAC contractors

### Business Pages (Optional)
- `/business/abc-electric/` - Single business page
- `/business/xyz-plumbing/` - Another business

### How It Works

Custom rewrite rules in `functions.php`:

```php
// Category pages
add_rewrite_rule(
    '^(electricians|plumbers|hvac|contractors)/?$',
    'index.php?category_landing=$matches[1]',
    'top'
);

// City-specific pages
add_rewrite_rule(
    '^(electricians|plumbers|hvac|contractors)/([^/]+)/?$',
    'index.php?category_landing=$matches[1]&city=$matches[2]',
    'top'
);
```

---

## SEO OPTIMIZATION

### Automatically Generated

- **Page Titles:** Dynamic based on category/city
- **Meta Descriptions:** Optimized for each category
- **Structured Data:** JSON-LD for LocalBusiness
- **Open Graph:** Social media sharing tags
- **Clean URLs:** `/electricians/` instead of `?page_id=123`

### Further Optimization

1. Install **Yoast SEO** plugin (optional)
2. Add category-specific content blocks
3. Create city-specific landing pages
4. Add customer testimonials
5. Create FAQ sections

---

## PERFORMANCE OPTIMIZATION

### Already Implemented

- Removed unnecessary WordPress features (emojis, XML-RPC, etc.)
- Minimal theme with no bloat
- Async script loading
- Clean database queries
- No plugin dependencies

### Additional Improvements

1. **Enable caching:**
   ```bash
   define('WP_CACHE', true);
   # Install W3 Total Cache or WP Super Cache plugin
   ```

2. **Enable Gzip compression** in `.htaccess`:
   ```apache
   <IfModule mod_deflate.c>
       AddOutputFilterByType DEFLATE text/html text/plain text/xml text/css text/javascript application/javascript
   </IfModule>
   ```

3. **Enable browser caching** in `.htaccess`:
   ```apache
   <IfModule mod_expires.c>
       ExpiresActive On
       ExpiresByType image/jpg "access plus 1 year"
       ExpiresByType image/jpeg "access plus 1 year"
       ExpiresByType image/png "access plus 1 year"
       ExpiresByType text/css "access plus 1 month"
       ExpiresByType application/javascript "access plus 1 month"
   </IfModule>
   ```

---

## SECURITY

### Built-in Security

- File editing disabled in admin
- XML-RPC disabled
- WordPress version hidden
- Admin bar hidden for non-admins
- Nonce verification on form submissions

### Additional Recommendations

1. **SSL Certificate:** Always use HTTPS
2. **Strong passwords:** For admin and database
3. **Regular updates:** Keep WordPress core updated
4. **Backup database:** Regular backups of MySQL database
5. **Security plugin:** Consider Wordfence or Sucuri

---

## TROUBLESHOOTING

### Issue: 404 on category pages

**Solution:** Flush rewrite rules
1. Go to WordPress admin
2. Settings → Permalinks
3. Click "Save Changes"

### Issue: Form submissions not working

**Check:**
1. Supabase credentials in `wp-config.php`
2. Browser console for JavaScript errors
3. WordPress admin → Tools → Site Health

**Debug:**
```php
// Add to wp-config.php temporarily
define('WP_DEBUG', true);
define('WP_DEBUG_LOG', true);
define('WP_DEBUG_DISPLAY', false);

// Check logs at: wp-content/debug.log
```

### Issue: No leads showing

**Check:**
1. Supabase has leads with `status='qualified'`
2. Supabase URL and API key are correct
3. PHP has curl extension installed: `php -m | grep curl`

**Test connection:**
```php
// Add to category template temporarily
echo '<pre>';
print_r($leads);
echo '</pre>';
```

### Issue: Styling not loading

**Solution:**
1. Check file permissions on `style.css`
2. Clear browser cache
3. Check theme is activated

---

## DEPLOYMENT

### Local Development

Use XAMPP, MAMP, or Local by Flywheel for local testing

### Production Deployment

**Option 1: Shared Hosting (cPanel)**
1. Upload files via FTP/SFTP
2. Create MySQL database via cPanel
3. Import database if migrating
4. Update `wp-config.php` with new credentials

**Option 2: VPS/Cloud**
1. Set up LAMP stack (Linux, Apache, MySQL, PHP)
2. Clone repository
3. Configure virtual host
4. Set up SSL with Let's Encrypt

**Option 3: Managed WordPress Hosting**
- WP Engine
- Kinsta
- Flywheel
(Upload theme via SFTP, configure Supabase credentials)

---

## MAINTENANCE

### Weekly
- Check form submissions
- Review analytics
- Test category pages

### Monthly
- Update WordPress core (if enabled)
- Backup MySQL database
- Review Supabase usage

### Quarterly
- Review and optimize content
- Update category pain points
- Add new service areas

---

## EXTENDING THE SYSTEM

### Add More Categories

1. Create new template in `page-templates/`
2. Register in `functions.php`
3. Add category content in `includes/dynamic-content.php`
4. Flush rewrite rules

### Add Blog

WordPress supports blogging out of the box. Just create posts!

### Add Thank You Page

Create a new page in WordPress:
1. Pages → Add New
2. Title: "Thank You"
3. Content: Custom thank you message
4. Publish
5. URL will be: `/thank-you/`

### Add Analytics

```php
// Add to functions.php
function rise_add_analytics() {
    ?>
    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){dataLayer.push(arguments);}
        gtag('js', new Date());
        gtag('config', 'GA_MEASUREMENT_ID');
    </script>
    <?php
}
add_action('wp_head', 'rise_add_analytics');
```

---

## SUPPORT

- **Documentation:** `/docs/WORDPRESS_LANDING_PAGES.md`
- **WordPress Codex:** https://codex.wordpress.org/
- **Supabase Docs:** https://supabase.com/docs

---

**WordPress Landing Pages System Complete**
**Status:** Ready for production deployment
**Version:** 1.0.0
