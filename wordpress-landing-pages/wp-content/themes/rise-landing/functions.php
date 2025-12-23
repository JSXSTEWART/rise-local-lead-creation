<?php
/**
 * Rise Landing Theme Functions
 * Stripped-down WordPress theme for dynamic lead generation landing pages
 *
 * @package RiseLanding
 * @version 1.0.0
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

// Load dependencies
require_once get_template_directory() . '/includes/supabase-client.php';
require_once get_template_directory() . '/includes/form-handler.php';
require_once get_template_directory() . '/includes/dynamic-content.php';

/**
 * Theme setup
 */
function rise_landing_setup() {
    // Remove unnecessary WordPress features
    remove_action('wp_head', 'print_emoji_detection_script', 7);
    remove_action('wp_print_styles', 'print_emoji_styles');
    remove_action('wp_head', 'wp_generator');
    remove_action('wp_head', 'wlwmanifest_link');
    remove_action('wp_head', 'rsd_link');
    remove_action('wp_head', 'wp_shortlink_wp_head');
    remove_action('wp_head', 'rest_output_link_wp_head');
    remove_action('wp_head', 'adjacent_posts_rel_link_wp_head', 10);

    // Disable XML-RPC
    add_filter('xmlrpc_enabled', '__return_false');

    // Disable pingbacks
    add_filter('wp_headers', function($headers) {
        unset($headers['X-Pingback']);
        return $headers;
    });

    // Clean up admin bar
    add_filter('show_admin_bar', '__return_false');

    // Add theme support
    add_theme_support('title-tag');
    add_theme_support('html5', ['search-form', 'comment-form', 'comment-list', 'gallery', 'caption']);

    // Register custom page templates
    add_filter('theme_page_templates', 'rise_landing_register_templates');
}
add_action('after_setup_theme', 'rise_landing_setup');

/**
 * Register custom page templates
 */
function rise_landing_register_templates($templates) {
    $templates['page-templates/category-electricians.php'] = 'Electricians Landing Page';
    $templates['page-templates/category-plumbers.php'] = 'Plumbers Landing Page';
    $templates['page-templates/category-hvac.php'] = 'HVAC Landing Page';
    $templates['page-templates/category-contractors.php'] = 'Contractors Landing Page';
    $templates['page-templates/single-business.php'] = 'Single Business Page';

    return $templates;
}

/**
 * Custom rewrite rules for clean URLs
 */
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

    // City pages: /electricians/austin/
    add_rewrite_rule(
        '^(electricians|plumbers|hvac|contractors)/([^/]+)/?$',
        'index.php?category_landing=$matches[1]&city=$matches[2]',
        'top'
    );
}
add_action('init', 'rise_landing_rewrite_rules');

/**
 * Register custom query vars
 */
function rise_landing_query_vars($vars) {
    $vars[] = 'category_landing';
    $vars[] = 'business_landing';
    $vars[] = 'city';
    return $vars;
}
add_filter('query_vars', 'rise_landing_query_vars');

/**
 * Route custom URLs to correct templates
 */
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

/**
 * Enqueue styles and scripts
 */
function rise_landing_enqueue_assets() {
    // Main stylesheet
    wp_enqueue_style('rise-landing-style', get_stylesheet_uri(), [], '1.0.0');

    // Google Fonts
    wp_enqueue_style(
        'google-fonts',
        'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&display=swap',
        [],
        null
    );

    // jQuery (already included in WordPress)
    wp_enqueue_script('jquery');

    // Custom JavaScript
    wp_enqueue_script(
        'rise-landing-scripts',
        get_template_directory_uri() . '/assets/js/main.js',
        ['jquery'],
        '1.0.0',
        true
    );

    // Pass AJAX URL and nonce to JavaScript
    wp_localize_script('rise-landing-scripts', 'riseAjax', [
        'ajaxurl' => admin_url('admin-ajax.php'),
        'nonce' => wp_create_nonce('rise_form_submit')
    ]);
}
add_action('wp_enqueue_scripts', 'rise_landing_enqueue_assets');

/**
 * AJAX form submission handlers
 */
add_action('wp_ajax_nopriv_submit_lead_form', 'rise_handle_form_submission');
add_action('wp_ajax_submit_lead_form', 'rise_handle_form_submission');

/**
 * Remove unnecessary admin menu items
 */
function rise_landing_remove_admin_menus() {
    // Only show essential menus
    remove_menu_page('edit-comments.php');  // Comments
    remove_menu_page('tools.php');          // Tools
}
add_action('admin_menu', 'rise_landing_remove_admin_menus');

/**
 * Disable comments completely
 */
function rise_landing_disable_comments() {
    // Close comments on the front-end
    add_filter('comments_open', '__return_false', 20, 2);
    add_filter('pings_open', '__return_false', 20, 2);

    // Hide existing comments
    add_filter('comments_array', '__return_empty_array', 10, 2);

    // Remove comments page in admin menu
    add_action('admin_init', function() {
        // Redirect any user trying to access comments page
        global $pagenow;

        if ($pagenow === 'edit-comments.php') {
            wp_redirect(admin_url());
            exit;
        }

        // Remove comments metabox from dashboard
        remove_meta_box('dashboard_recent_comments', 'dashboard', 'normal');

        // Disable support for comments and trackbacks in post types
        foreach (get_post_types() as $post_type) {
            if (post_type_supports($post_type, 'comments')) {
                remove_post_type_support($post_type, 'comments');
                remove_post_type_support($post_type, 'trackbacks');
            }
        }
    });

    // Close comments on the front-end for all posts
    add_filter('comments_open', '__return_false', 20, 2);
}
add_action('init', 'rise_landing_disable_comments');

/**
 * Custom login logo
 */
function rise_landing_login_logo() {
    ?>
    <style type="text/css">
        #login h1 a, .login h1 a {
            background-image: none;
            background-size: contain;
            height: 65px;
            width: 320px;
            margin-bottom: 20px;
        }
        #login h1 a::before {
            content: '🚀 Rise Local';
            font-size: 32px;
            font-weight: 800;
            color: #667eea;
        }
    </style>
    <?php
}
add_action('login_enqueue_scripts', 'rise_landing_login_logo');

/**
 * Custom login logo URL
 */
function rise_landing_login_logo_url() {
    return home_url();
}
add_filter('login_headerurl', 'rise_landing_login_logo_url');

/**
 * Flush rewrite rules on theme activation
 */
function rise_landing_activation() {
    rise_landing_rewrite_rules();
    flush_rewrite_rules();
}
add_action('after_switch_theme', 'rise_landing_activation');

/**
 * Helper function to get category display name
 */
function rise_get_category_display_name($category) {
    $names = [
        'electricians' => 'Electricians',
        'plumbers' => 'Plumbers',
        'hvac' => 'HVAC Contractors',
        'contractors' => 'General Contractors'
    ];

    return $names[$category] ?? ucfirst($category);
}

/**
 * Helper function to get category icon
 */
function rise_get_category_icon($category) {
    $icons = [
        'electricians' => '⚡',
        'plumbers' => '🔧',
        'hvac' => '❄️',
        'contractors' => '🏗️'
    ];

    return $icons[$category] ?? '🏢';
}

/**
 * Helper function to sanitize slug
 */
function rise_sanitize_slug($text) {
    $text = strtolower($text);
    $text = preg_replace('/[^a-z0-9\s-]/', '', $text);
    $text = preg_replace('/[\s-]+/', '-', $text);
    $text = trim($text, '-');

    return $text;
}

/**
 * Security: Disable file editing in admin
 */
if (!defined('DISALLOW_FILE_EDIT')) {
    define('DISALLOW_FILE_EDIT', true);
}

/**
 * Performance: Limit post revisions
 */
if (!defined('WP_POST_REVISIONS')) {
    define('WP_POST_REVISIONS', 3);
}

/**
 * Security: Hide WordPress version
 */
remove_action('wp_head', 'wp_generator');
add_filter('the_generator', '__return_empty_string');

/**
 * Performance: Remove query strings from static resources
 */
function rise_remove_query_strings($src) {
    if (strpos($src, 'ver=')) {
        $src = remove_query_arg('ver', $src);
    }
    return $src;
}
add_filter('style_loader_src', 'rise_remove_query_strings', 10, 2);
add_filter('script_loader_src', 'rise_remove_query_strings', 10, 2);

/**
 * Custom excerpt length
 */
function rise_excerpt_length($length) {
    return 30;
}
add_filter('excerpt_length', 'rise_excerpt_length');

/**
 * Add async/defer to scripts
 */
function rise_async_scripts($tag, $handle) {
    if ('rise-landing-scripts' === $handle) {
        return str_replace(' src', ' defer src', $tag);
    }
    return $tag;
}
add_filter('script_loader_tag', 'rise_async_scripts', 10, 2);
