# WordPress Dynamic Landing Page System
## Stripped-Down WordPress for Multi-Category Lead Generation

**Purpose:** Create category-specific landing pages using minimal WordPress installation
**Integration:** Connects with Rise Local pipeline and Supabase database
**Technology:** PHP, WordPress Core (stripped), Custom Theme, MySQL

---

## TABLE OF CONTENTS

1. [Architecture Overview](#architecture-overview)
2. [WordPress Minimal Installation](#wordpress-minimal-installation)
3. [Custom Theme Structure](#custom-theme-structure)
4. [Dynamic Page Templates](#dynamic-page-templates)
5. [Database Integration](#database-integration)
6. [Deployment Guide](#deployment-guide)

---

## ARCHITECTURE OVERVIEW

### What We're Building

A **lightweight WordPress installation** that:
- ✅ Generates dynamic landing pages per business category
- ✅ Pulls lead data from Supabase
- ✅ Creates custom pages for electricians, plumbers, HVAC, etc.
- ✅ Integrates form submissions back to pipeline
- ❌ NO blog, comments, media library, admin bloat
- ❌ NO unnecessary plugins or themes

### System Flow

```
Supabase Leads DB
       ↓
WordPress (PHP) ← Custom Theme Templates
       ↓
Dynamic Landing Pages:
  - /electricians/
  - /plumbers/
  - /hvac/
  - /lead/{business-name}/
       ↓
Form Submission → Supabase → Rise Pipeline
```

### File Structure

```
wordpress-landing-pages/
├── wp-config.php              # Custom config (connects to MySQL)
├── index.php                  # WordPress core
├── wp-content/
│   └── themes/
│       └── rise-landing/      # Our custom theme
│           ├── style.css
│           ├── functions.php  # Custom functions
│           ├── index.php
│           ├── page-templates/
│           │   ├── category-electricians.php
│           │   ├── category-plumbers.php
│           │   ├── category-hvac.php
│           │   └── single-business.php
│           ├── includes/
│           │   ├── supabase-client.php
│           │   ├── form-handler.php
│           │   └── dynamic-content.php
│           └── assets/
│               ├── css/
│               ├── js/
│               └── images/
└── .htaccess                  # Clean URLs
```

---

## WORDPRESS MINIMAL INSTALLATION

### What to Remove from WordPress

**Remove these directories:**
```bash
# NOT NEEDED - Delete these
wp-content/plugins/         # No plugins needed initially
wp-content/themes/twenty*   # Remove default themes
wp-admin/themes.php         # Disable theme switching
wp-admin/plugins.php        # Disable plugin management
wp-admin/tools.php          # Remove tools
wp-admin/comments.php       # No comments needed
```

**Disable features in `wp-config.php`:**
```php
// Disable features we don't need
define('DISALLOW_FILE_EDIT', true);   // No theme/plugin editor
define('DISALLOW_FILE_MODS', true);   // No updates from admin
define('WP_POST_REVISIONS', false);   // No revisions
define('AUTOSAVE_INTERVAL', 300);     // Reduce autosave
define('WP_CRON_LOCK_TIMEOUT', 60);   // Optimize cron

// Disable feeds, pingbacks, trackbacks
add_filter('pre_option_rss_language', '__return_empty_string');
add_filter('wp_headers', function($headers) {
    unset($headers['X-Pingback']);
    return $headers;
});
```

### Custom `wp-config.php` Setup

```php
<?php
/**
 * Rise Local Landing Pages - WordPress Configuration
 * Minimal WordPress setup for dynamic landing pages
 */

// Load environment variables from parent project
require_once(__DIR__ . '/../vendor/autoload.php');
$dotenv = Dotenv\Dotenv::createImmutable(__DIR__ . '/..');
$dotenv->load();

// Database Settings (WordPress needs MySQL for content management)
define('DB_NAME', $_ENV['WP_DB_NAME'] ?? 'rise_landing_pages');
define('DB_USER', $_ENV['WP_DB_USER'] ?? 'root');
define('DB_PASSWORD', $_ENV['WP_DB_PASSWORD'] ?? '');
define('DB_HOST', $_ENV['WP_DB_HOST'] ?? 'localhost');
define('DB_CHARSET', 'utf8mb4');
define('DB_COLLATE', '');

// Supabase Connection (for lead data)
define('SUPABASE_URL', $_ENV['SUPABASE_URL']);
define('SUPABASE_KEY', $_ENV['SUPABASE_SERVICE_KEY']);

// Security Keys (generate at https://api.wordpress.org/secret-key/1.1/salt/)
define('AUTH_KEY',         'put-unique-phrase-here');
define('SECURE_AUTH_KEY',  'put-unique-phrase-here');
define('LOGGED_IN_KEY',    'put-unique-phrase-here');
define('NONCE_KEY',        'put-unique-phrase-here');
define('AUTH_SALT',        'put-unique-phrase-here');
define('SECURE_AUTH_SALT', 'put-unique-phrase-here');
define('LOGGED_IN_SALT',   'put-unique-phrase-here');
define('NONCE_SALT',       'put-unique-phrase-here');

// WordPress Database Table Prefix
$table_prefix = 'wp_';

// Disable WordPress features we don't need
define('DISALLOW_FILE_EDIT', true);
define('DISALLOW_FILE_MODS', true);
define('WP_POST_REVISIONS', false);
define('AUTOSAVE_INTERVAL', 300);
define('WP_AUTO_UPDATE_CORE', false);
define('AUTOMATIC_UPDATER_DISABLED', true);

// Performance optimizations
define('WP_MEMORY_LIMIT', '128M');
define('WP_MAX_MEMORY_LIMIT', '256M');
define('WP_CACHE', true);

// Debug (disable in production)
define('WP_DEBUG', false);
define('WP_DEBUG_LOG', false);
define('WP_DEBUG_DISPLAY', false);

// Absolute path to WordPress directory
if (!defined('ABSPATH')) {
    define('ABSPATH', __DIR__ . '/');
}

// Sets up WordPress vars and included files
require_once ABSPATH . 'wp-settings.php';
```

---

## CUSTOM THEME STRUCTURE

### Theme: `rise-landing`

#### `style.css` (Theme Header)
```css
/*
Theme Name: Rise Landing Pages
Theme URI: https://github.com/your-org/rise-local-lead-creation
Description: Minimal WordPress theme for dynamic category landing pages
Version: 1.0.0
Author: Rise Local
Author URI: https://riselocal.com
License: MIT
Text Domain: rise-landing
*/

/* Reset and Base Styles */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    line-height: 1.6;
    color: #333;
    background: #f8f9fa;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}

/* Hero Section */
.hero {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 100px 20px;
    text-align: center;
}

.hero h1 {
    font-size: 3.5rem;
    font-weight: 800;
    margin-bottom: 20px;
}

.hero p {
    font-size: 1.25rem;
    margin-bottom: 30px;
}

/* Form Styles */
.lead-form {
    background: white;
    padding: 40px;
    border-radius: 12px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.1);
    max-width: 600px;
    margin: -50px auto 50px;
}

.form-group {
    margin-bottom: 20px;
}

.form-group label {
    display: block;
    margin-bottom: 8px;
    font-weight: 600;
    color: #555;
}

.form-group input,
.form-group textarea {
    width: 100%;
    padding: 12px 16px;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    font-size: 16px;
    transition: border-color 0.3s;
}

.form-group input:focus,
.form-group textarea:focus {
    outline: none;
    border-color: #667eea;
}

.btn-submit {
    width: 100%;
    padding: 16px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 18px;
    font-weight: 700;
    cursor: pointer;
    transition: transform 0.2s;
}

.btn-submit:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

/* Stats Section */
.stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 30px;
    padding: 60px 20px;
}

.stat-card {
    background: white;
    padding: 30px;
    border-radius: 12px;
    text-align: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

.stat-number {
    font-size: 3rem;
    font-weight: 800;
    color: #667eea;
    margin-bottom: 10px;
}

.stat-label {
    font-size: 1rem;
    color: #666;
}

/* Responsive */
@media (max-width: 768px) {
    .hero h1 {
        font-size: 2rem;
    }

    .lead-form {
        padding: 30px 20px;
        margin: -30px 20px 30px;
    }
}
```

#### `functions.php` (Theme Functions)
```php
<?php
/**
 * Rise Landing Theme Functions
 * Custom functionality for dynamic landing pages
 */

// Load dependencies
require_once get_template_directory() . '/includes/supabase-client.php';
require_once get_template_directory() . '/includes/form-handler.php';
require_once get_template_directory() . '/includes/dynamic-content.php';

// Theme setup
function rise_landing_setup() {
    // Remove unnecessary WordPress features
    remove_action('wp_head', 'print_emoji_detection_script', 7);
    remove_action('wp_print_styles', 'print_emoji_styles');
    remove_action('wp_head', 'wp_generator');
    remove_action('wp_head', 'wlwmanifest_link');
    remove_action('wp_head', 'rsd_link');
    remove_action('wp_head', 'wp_shortlink_wp_head');
    remove_action('wp_head', 'rest_output_link_wp_head');

    // Clean up admin bar
    add_filter('show_admin_bar', '__return_false');

    // Register custom page templates
    add_filter('theme_page_templates', 'rise_landing_register_templates');
}
add_action('after_setup_theme', 'rise_landing_setup');

// Register custom page templates
function rise_landing_register_templates($templates) {
    $templates['page-templates/category-electricians.php'] = 'Electricians Landing Page';
    $templates['page-templates/category-plumbers.php'] = 'Plumbers Landing Page';
    $templates['page-templates/category-hvac.php'] = 'HVAC Landing Page';
    $templates['page-templates/single-business.php'] = 'Single Business Page';

    return $templates;
}

// Custom rewrite rules for clean URLs
function rise_landing_rewrite_rules() {
    // Category pages: /electricians/, /plumbers/, etc.
    add_rewrite_rule(
        '^(electricians|plumbers|hvac|contractors)/?$',
        'index.php?category_landing=$matches[1]',
        'top'
    );

    // Business pages: /business/abc-electric/
    add_rewrite_rule(
        '^business/([^/]+)/?$',
        'index.php?business_landing=$matches[1]',
        'top'
    );
}
add_action('init', 'rise_landing_rewrite_rules');

// Register custom query vars
function rise_landing_query_vars($vars) {
    $vars[] = 'category_landing';
    $vars[] = 'business_landing';
    return $vars;
}
add_filter('query_vars', 'rise_landing_query_vars');

// Route custom URLs to correct templates
function rise_landing_template_redirect() {
    global $wp_query;

    // Category landing pages
    if (get_query_var('category_landing')) {
        $category = get_query_var('category_landing');
        $template = get_template_directory() . "/page-templates/category-{$category}.php";

        if (file_exists($template)) {
            include $template;
            exit;
        }
    }

    // Business landing pages
    if (get_query_var('business_landing')) {
        $business_slug = get_query_var('business_landing');
        $template = get_template_directory() . '/page-templates/single-business.php';

        if (file_exists($template)) {
            include $template;
            exit;
        }
    }
}
add_action('template_redirect', 'rise_landing_template_redirect');

// Enqueue styles and scripts
function rise_landing_enqueue_assets() {
    // Main stylesheet
    wp_enqueue_style('rise-landing-style', get_stylesheet_uri(), [], '1.0.0');

    // Google Fonts
    wp_enqueue_style(
        'google-fonts',
        'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap',
        [],
        null
    );

    // Custom JavaScript
    wp_enqueue_script(
        'rise-landing-scripts',
        get_template_directory_uri() . '/assets/js/main.js',
        ['jquery'],
        '1.0.0',
        true
    );

    // Pass AJAX URL to JavaScript
    wp_localize_script('rise-landing-scripts', 'riseAjax', [
        'ajaxurl' => admin_url('admin-ajax.php'),
        'nonce' => wp_create_nonce('rise_form_submit')
    ]);
}
add_action('wp_enqueue_scripts', 'rise_landing_enqueue_assets');

// AJAX form submission handler
add_action('wp_ajax_nopriv_submit_lead_form', 'rise_handle_form_submission');
add_action('wp_ajax_submit_lead_form', 'rise_handle_form_submission');

// Disable WordPress features we don't need
add_filter('xmlrpc_enabled', '__return_false');
remove_action('wp_head', 'adjacent_posts_rel_link_wp_head', 10);
```

#### `includes/supabase-client.php` (Supabase Integration)
```php
<?php
/**
 * Supabase Client for WordPress
 * Connects to Supabase database to fetch lead data
 */

class Rise_Supabase_Client {
    private $base_url;
    private $api_key;

    public function __construct() {
        $this->base_url = SUPABASE_URL . '/rest/v1';
        $this->api_key = SUPABASE_KEY;
    }

    /**
     * Get leads by category
     */
    public function get_leads_by_category($category, $limit = 10) {
        $url = $this->base_url . '/leads';
        $url .= '?status=eq.qualified';
        $url .= '&address_state=eq.TX';
        $url .= '&limit=' . intval($limit);
        $url .= '&order=created_at.desc';

        $response = wp_remote_get($url, [
            'headers' => [
                'apikey' => $this->api_key,
                'Authorization' => 'Bearer ' . $this->api_key,
                'Content-Type' => 'application/json'
            ],
            'timeout' => 15
        ]);

        if (is_wp_error($response)) {
            error_log('Supabase API Error: ' . $response->get_error_message());
            return [];
        }

        $body = wp_remote_retrieve_body($response);
        $data = json_decode($body, true);

        return $data ?? [];
    }

    /**
     * Get single business by slug
     */
    public function get_business_by_slug($slug) {
        // Convert slug to business name (abc-electric -> ABC Electric)
        $business_name = ucwords(str_replace('-', ' ', $slug));

        $url = $this->base_url . '/leads';
        $url .= '?business_name=ilike.*' . urlencode($business_name) . '*';
        $url .= '&limit=1';

        $response = wp_remote_get($url, [
            'headers' => [
                'apikey' => $this->api_key,
                'Authorization' => 'Bearer ' . $this->api_key,
                'Content-Type' => 'application/json'
            ],
            'timeout' => 15
        ]);

        if (is_wp_error($response)) {
            return null;
        }

        $body = wp_remote_retrieve_body($response);
        $data = json_decode($body, true);

        return $data[0] ?? null;
    }

    /**
     * Submit new lead to Supabase
     */
    public function create_lead($lead_data) {
        $url = $this->base_url . '/leads';

        $response = wp_remote_post($url, [
            'headers' => [
                'apikey' => $this->api_key,
                'Authorization' => 'Bearer ' . $this->api_key,
                'Content-Type' => 'application/json',
                'Prefer' => 'return=representation'
            ],
            'body' => json_encode($lead_data),
            'timeout' => 15
        ]);

        if (is_wp_error($response)) {
            error_log('Supabase Create Lead Error: ' . $response->get_error_message());
            return false;
        }

        $code = wp_remote_retrieve_response_code($response);
        return $code === 201;
    }
}

// Global instance
function rise_supabase() {
    static $instance = null;

    if ($instance === null) {
        $instance = new Rise_Supabase_Client();
    }

    return $instance;
}
```

#### `includes/form-handler.php` (Form Processing)
```php
<?php
/**
 * Form Handler for Lead Submissions
 * Processes form data and submits to Supabase
 */

function rise_handle_form_submission() {
    // Verify nonce
    if (!isset($_POST['nonce']) || !wp_verify_nonce($_POST['nonce'], 'rise_form_submit')) {
        wp_send_json_error(['message' => 'Security check failed']);
        return;
    }

    // Sanitize input
    $business_name = sanitize_text_field($_POST['business_name'] ?? '');
    $contact_name = sanitize_text_field($_POST['contact_name'] ?? '');
    $email = sanitize_email($_POST['email'] ?? '');
    $phone = sanitize_text_field($_POST['phone'] ?? '');
    $website = esc_url_raw($_POST['website'] ?? '');
    $address = sanitize_text_field($_POST['address'] ?? '');
    $city = sanitize_text_field($_POST['city'] ?? '');
    $state = sanitize_text_field($_POST['state'] ?? 'TX');
    $zip = sanitize_text_field($_POST['zip'] ?? '');
    $category = sanitize_text_field($_POST['category'] ?? 'electrician');
    $message = sanitize_textarea_field($_POST['message'] ?? '');

    // Validate required fields
    if (empty($business_name) || empty($email) || empty($phone)) {
        wp_send_json_error(['message' => 'Please fill in all required fields']);
        return;
    }

    // Prepare lead data
    $lead_data = [
        'business_name' => $business_name,
        'owner_name' => $contact_name,
        'owner_email' => $email,
        'phone' => $phone,
        'website' => $website,
        'address_full' => $address,
        'address_city' => $city,
        'address_state' => $state,
        'address_zip' => $zip,
        'status' => 'new',
        'source' => 'landing_page',
        'category' => $category,
        'notes' => $message,
        'created_at' => gmdate('Y-m-d\TH:i:s\Z')
    ];

    // Submit to Supabase
    $supabase = rise_supabase();
    $success = $supabase->create_lead($lead_data);

    if ($success) {
        // Send notification email (optional)
        wp_mail(
            get_option('admin_email'),
            'New Lead from Landing Page: ' . $business_name,
            "New lead submitted:\n\n" . print_r($lead_data, true)
        );

        wp_send_json_success([
            'message' => 'Thank you! We\'ll be in touch soon.',
            'redirect' => '/thank-you/'
        ]);
    } else {
        wp_send_json_error(['message' => 'Something went wrong. Please try again.']);
    }
}
```

---

## DYNAMIC PAGE TEMPLATES

### `page-templates/category-electricians.php`

```php
<?php
/**
 * Template Name: Electricians Landing Page
 * Dynamic landing page for electrician category
 */

// Get qualified electrician leads from Supabase
$supabase = rise_supabase();
$leads = $supabase->get_leads_by_category('electrician', 10);

// Calculate stats
$total_leads = count($leads);
$avg_rating = 0;
$total_reviews = 0;

foreach ($leads as $lead) {
    if (!empty($lead['google_rating'])) {
        $avg_rating += floatval($lead['google_rating']);
    }
    if (!empty($lead['google_review_count'])) {
        $total_reviews += intval($lead['google_review_count']);
    }
}

$avg_rating = $total_leads > 0 ? round($avg_rating / $total_leads, 1) : 0;
?>
<!DOCTYPE html>
<html <?php language_attributes(); ?>>
<head>
    <meta charset="<?php bloginfo('charset'); ?>">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Find Top-Rated Electricians in Texas | Rise Local</title>
    <meta name="description" content="Connect with pre-qualified, licensed electricians in Texas. Free quotes, verified reviews, and instant service.">
    <?php wp_head(); ?>
</head>
<body class="category-electricians">

<!-- Hero Section -->
<section class="hero">
    <div class="container">
        <h1>🔌 Find Your Perfect Electrician in Texas</h1>
        <p>Pre-qualified, licensed professionals ready to help</p>
        <div class="hero-stats">
            <span><?php echo $total_leads; ?>+ Verified Electricians</span>
            <span><?php echo $avg_rating; ?>⭐ Average Rating</span>
            <span><?php echo number_format($total_reviews); ?>+ Customer Reviews</span>
        </div>
    </div>
</section>

<!-- Lead Form -->
<section class="container">
    <form id="lead-form" class="lead-form">
        <h2>Get Free Quotes from Top Electricians</h2>
        <p>Fill out this form and we'll connect you with 3 pre-screened electricians in your area.</p>

        <div class="form-group">
            <label for="business_name">Business Name *</label>
            <input type="text" id="business_name" name="business_name" required>
        </div>

        <div class="form-group">
            <label for="contact_name">Your Name *</label>
            <input type="text" id="contact_name" name="contact_name" required>
        </div>

        <div class="form-group">
            <label for="email">Email *</label>
            <input type="email" id="email" name="email" required>
        </div>

        <div class="form-group">
            <label for="phone">Phone *</label>
            <input type="tel" id="phone" name="phone" required>
        </div>

        <div class="form-group">
            <label for="city">City *</label>
            <input type="text" id="city" name="city" required>
        </div>

        <div class="form-group">
            <label for="message">What electrical work do you need?</label>
            <textarea id="message" name="message" rows="4"></textarea>
        </div>

        <input type="hidden" name="category" value="electrician">
        <input type="hidden" name="action" value="submit_lead_form">

        <button type="submit" class="btn-submit">Get Free Quotes</button>
    </form>
</section>

<!-- Featured Electricians -->
<section class="container">
    <h2 style="text-align: center; margin: 60px 0 40px;">Featured Electricians in Your Area</h2>

    <div class="stats">
        <?php foreach (array_slice($leads, 0, 6) as $lead): ?>
            <div class="stat-card">
                <h3><?php echo esc_html($lead['business_name']); ?></h3>
                <div class="stat-number"><?php echo esc_html($lead['google_rating'] ?? 'N/A'); ?>⭐</div>
                <div class="stat-label">
                    <?php echo esc_html($lead['address_city'] ?? ''); ?>, TX<br>
                    <?php echo esc_html($lead['google_review_count'] ?? 0); ?> Reviews<br>
                    <?php if (!empty($lead['license_number'])): ?>
                        License: <?php echo esc_html($lead['license_number']); ?>
                    <?php endif; ?>
                </div>
                <?php if (!empty($lead['website'])): ?>
                    <a href="<?php echo esc_url($lead['website']); ?>" target="_blank" class="btn-visit">Visit Website</a>
                <?php endif; ?>
            </div>
        <?php endforeach; ?>
    </div>
</section>

<!-- Trust Signals -->
<section class="container" style="padding: 60px 20px;">
    <div style="text-align: center; max-width: 800px; margin: 0 auto;">
        <h2>Why Choose Rise Local?</h2>
        <div class="trust-grid">
            <div>
                <h3>✅ Pre-Qualified</h3>
                <p>Every electrician is verified, licensed, and pre-screened</p>
            </div>
            <div>
                <h3>🏆 Top-Rated</h3>
                <p>Only businesses with 4+ star ratings and positive reviews</p>
            </div>
            <div>
                <h3>⚡ Fast Response</h3>
                <p>Get quotes from 3 electricians within 24 hours</p>
            </div>
            <div>
                <h3>💯 Free Service</h3>
                <p>No fees, no commitments - completely free for you</p>
            </div>
        </div>
    </div>
</section>

<?php wp_footer(); ?>

<script>
jQuery(document).ready(function($) {
    $('#lead-form').on('submit', function(e) {
        e.preventDefault();

        const formData = $(this).serialize() + '&nonce=<?php echo wp_create_nonce("rise_form_submit"); ?>';
        const $btn = $(this).find('.btn-submit');
        const originalText = $btn.text();

        $btn.text('Submitting...').prop('disabled', true);

        $.post(riseAjax.ajaxurl, formData, function(response) {
            if (response.success) {
                alert(response.data.message);
                if (response.data.redirect) {
                    window.location.href = response.data.redirect;
                } else {
                    $('#lead-form')[0].reset();
                }
            } else {
                alert(response.data.message || 'Error submitting form');
            }
        }).fail(function() {
            alert('Network error. Please try again.');
        }).always(function() {
            $btn.text(originalText).prop('disabled', false);
        });
    });
});
</script>

</body>
</html>
```

---

## DATABASE INTEGRATION

### WordPress MySQL Setup (for content management)

```sql
-- WordPress needs MySQL for its own content management
-- This is SEPARATE from Supabase (which holds lead data)

CREATE DATABASE rise_landing_pages CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- WordPress will create its own tables on installation:
-- wp_posts, wp_users, wp_options, etc.
```

### Dual Database Architecture

```
WordPress MySQL          Supabase PostgreSQL
     ↓                          ↓
Content Management        Lead Data Storage
- Pages                   - Leads table
- Settings                - Pre-qualification data
- Admin users             - Enrichment data
     ↓                          ↓
     └──────── PHP ─────────────┘
              ↓
         Landing Pages
```

---

## DEPLOYMENT GUIDE

### Step 1: Install WordPress Core

```bash
cd /home/user/rise-local-lead-creation
mkdir wordpress-landing-pages
cd wordpress-landing-pages

# Download WordPress
wget https://wordpress.org/latest.tar.gz
tar -xzf latest.tar.gz
mv wordpress/* .
rm -rf wordpress latest.tar.gz
```

### Step 2: Setup MySQL Database

```bash
# Connect to MySQL
mysql -u root -p

# Create database
CREATE DATABASE rise_landing_pages CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'wp_user'@'localhost' IDENTIFIED BY 'secure_password_here';
GRANT ALL PRIVILEGES ON rise_landing_pages.* TO 'wp_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Step 3: Configure WordPress

```bash
# Copy custom wp-config.php
cp wp-config-sample.php wp-config.php

# Edit with your database credentials
nano wp-config.php
```

### Step 4: Install Custom Theme

```bash
# Create theme directory
mkdir -p wp-content/themes/rise-landing/{page-templates,includes,assets/{css,js,images}}

# Copy theme files (create each file from templates above)
# - style.css
# - functions.php
# - index.php
# - includes/supabase-client.php
# - includes/form-handler.php
# - includes/dynamic-content.php
# - page-templates/category-electricians.php
# etc.
```

### Step 5: Set Permissions

```bash
# Set ownership
sudo chown -R www-data:www-data /path/to/wordpress-landing-pages

# Set permissions
find . -type d -exec chmod 755 {} \;
find . -type f -exec chmod 644 {} \;
```

### Step 6: Complete WordPress Installation

```
1. Visit: http://your-domain.com/wp-admin/install.php
2. Complete 5-minute installation
3. Login to admin
4. Go to Appearance → Themes
5. Activate "Rise Landing Pages" theme
6. Go to Settings → Permalinks → Select "Post name"
7. Save changes (this activates rewrite rules)
```

### Step 7: Create Landing Pages

```
1. Pages → Add New
2. Title: "Electricians"
3. Template: Select "Electricians Landing Page"
4. Publish
5. Visit: http://your-domain.com/electricians/
```

### Step 8: Update Environment Variables

```bash
# Add to main .env file
WP_DB_NAME=rise_landing_pages
WP_DB_USER=wp_user
WP_DB_PASSWORD=secure_password_here
WP_DB_HOST=localhost
```

---

## NEXT STEPS

### Additional Category Templates to Create

1. `category-plumbers.php`
2. `category-hvac.php`
3. `category-contractors.php`
4. `category-roofers.php`

### Enhancements

- **A/B Testing:** Different hero copy per category
- **Dynamic Pricing:** Pull tech stack data to show "Website Upgrade Needed"
- **Lead Scoring:** Show only highest-quality leads
- **Real-time Updates:** WebSocket connection to Supabase
- **Analytics:** Track conversions, form submissions
- **SEO:** Dynamic meta tags per category

---

**WordPress Landing Page System Complete**
**Status:** Ready for implementation
**Integration:** Connects to existing Supabase + Rise Pipeline
