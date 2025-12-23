<?php
/**
 * Template Name: Electricians Landing Page
 * Dynamic landing page for electrician category with Supabase integration
 *
 * @package RiseLanding
 * @version 1.0.0
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

// Get leads from Supabase
$supabase = rise_supabase();
$category = 'electrician';
$city = get_query_var('city') ?: '';

// Filters
$filters = ['state' => 'TX'];
if ($city) {
    $filters['city'] = $city;
}

$leads = $supabase->get_leads_by_category($category, 12, $filters);
$stats = $supabase->get_category_stats($category);

// Calculate display stats
$total_businesses = $stats['total_businesses'] ?? count($leads);
$avg_rating = $stats['avg_rating'] ?? 0;
$total_reviews = $stats['total_reviews'] ?? 0;

// Get dynamic content
$pain_points = rise_get_category_pain_points('electricians');
$benefits = rise_get_category_benefits('electricians');
$service_areas = rise_get_service_areas('electricians');

// SEO
$page_title = $city ? "Find Licensed Electricians in $city, Texas" : "Find Licensed Electricians in Texas";
$meta_description = "Connect with pre-qualified, licensed electricians in Texas. Get free quotes from top-rated electrical contractors. Licensed, insured, and ready to help.";
?>
<!DOCTYPE html>
<html <?php language_attributes(); ?>>
<head>
    <meta charset="<?php bloginfo('charset'); ?>">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo esc_html($page_title); ?> | Rise Local</title>
    <meta name="description" content="<?php echo esc_attr($meta_description); ?>">
    <meta name="robots" content="index, follow">

    <!-- Open Graph -->
    <meta property="og:title" content="<?php echo esc_attr($page_title); ?>">
    <meta property="og:description" content="<?php echo esc_attr($meta_description); ?>">
    <meta property="og:type" content="website">
    <meta property="og:url" content="<?php echo esc_url(home_url($_SERVER['REQUEST_URI'])); ?>">

    <?php wp_head(); ?>

    <!-- Structured Data -->
    <?php echo rise_generate_structured_data('electricians'); ?>
</head>
<body class="category-electricians <?php echo $city ? 'city-' . sanitize_title($city) : ''; ?>">

<!-- Hero Section -->
<section class="hero">
    <div class="hero-content container">
        <h1><?php echo rise_get_category_icon('electricians'); ?> <?php echo esc_html($page_title); ?></h1>
        <p>Pre-qualified, licensed professionals ready to help <?php echo $city ? 'in ' . esc_html($city) : 'across Texas'; ?></p>

        <?php if ($total_businesses > 0): ?>
        <div class="hero-stats">
            <span><strong><?php echo number_format($total_businesses); ?>+</strong> Verified Electricians</span>
            <span><strong><?php echo number_format($avg_rating, 1); ?></strong>⭐ Average Rating</span>
            <span><strong><?php echo number_format($total_reviews); ?>+</strong> Customer Reviews</span>
        </div>
        <?php endif; ?>
    </div>
</section>

<!-- Lead Form -->
<section class="container">
    <form id="lead-form" class="lead-form">
        <h2>Get Free Quotes from Top Electricians</h2>
        <p>Fill out this form and we'll connect you with 3 pre-screened electricians in your area within 24 hours.</p>

        <div class="form-group">
            <label for="business_name">Business Name *</label>
            <input type="text" id="business_name" name="business_name" placeholder="ABC Electric" required>
        </div>

        <div class="form-group">
            <label for="contact_name">Contact Name *</label>
            <input type="text" id="contact_name" name="contact_name" placeholder="John Doe" required>
        </div>

        <div class="form-row">
            <div class="form-group">
                <label for="email">Email *</label>
                <input type="email" id="email" name="email" placeholder="john@example.com" required>
            </div>

            <div class="form-group">
                <label for="phone">Phone *</label>
                <input type="tel" id="phone" name="phone" placeholder="(555) 123-4567" required>
            </div>
        </div>

        <div class="form-group">
            <label for="website">Website (Optional)</label>
            <input type="url" id="website" name="website" placeholder="https://yourwebsite.com">
        </div>

        <div class="form-row">
            <div class="form-group">
                <label for="city">City *</label>
                <input type="text" id="city" name="city" value="<?php echo esc_attr($city); ?>" placeholder="Austin" required>
            </div>

            <div class="form-group">
                <label for="state">State *</label>
                <select id="state" name="state" required>
                    <option value="TX" selected>Texas</option>
                </select>
            </div>
        </div>

        <div class="form-group">
            <label for="message">What electrical work do you need? (Optional)</label>
            <textarea id="message" name="message" rows="4" placeholder="Tell us about your project..."></textarea>
        </div>

        <input type="hidden" name="category" value="electrician">

        <button type="submit" class="btn-submit">Get Free Quotes</button>

        <p style="margin-top: 15px; font-size: 0.9rem; color: #666; text-align: center;">
            By submitting, you agree to be contacted by Rise Local and our partner electricians.
        </p>
    </form>
</section>

<!-- Featured Electricians -->
<?php if (!empty($leads)): ?>
<section class="container">
    <h2 style="text-align: center; margin: 60px 0 40px; font-size: 2.5rem; color: #333;">
        Featured Electricians <?php echo $city ? 'in ' . esc_html($city) : 'in Your Area'; ?>
    </h2>

    <div class="business-grid">
        <?php foreach ($leads as $lead): ?>
            <div class="business-card">
                <h3><?php echo esc_html($lead['business_name']); ?></h3>

                <?php if (!empty($lead['google_rating'])): ?>
                    <div class="business-rating">
                        <?php echo number_format($lead['google_rating'], 1); ?>⭐
                    </div>
                <?php endif; ?>

                <div class="business-details">
                    <?php if (!empty($lead['address_city'])): ?>
                        <div>📍 <?php echo esc_html($lead['address_city']); ?>, TX</div>
                    <?php endif; ?>

                    <?php if (!empty($lead['google_review_count'])): ?>
                        <div>💬 <?php echo number_format($lead['google_review_count']); ?> Reviews</div>
                    <?php endif; ?>

                    <?php if (!empty($lead['license_number'])): ?>
                        <div>✅ License: <?php echo esc_html($lead['license_number']); ?></div>
                    <?php endif; ?>

                    <?php if (!empty($lead['phone'])): ?>
                        <div>📞 <?php echo esc_html($lead['phone']); ?></div>
                    <?php endif; ?>
                </div>

                <?php if (!empty($lead['license_status']) && $lead['license_status'] === 'Active'): ?>
                    <span class="business-badge">✓ Licensed & Verified</span>
                <?php endif; ?>

                <?php if (!empty($lead['website'])): ?>
                    <a href="<?php echo esc_url($lead['website']); ?>" target="_blank" rel="noopener" class="btn-visit">
                        Visit Website →
                    </a>
                <?php endif; ?>
            </div>
        <?php endforeach; ?>
    </div>
</section>
<?php endif; ?>

<!-- Trust Signals -->
<section class="trust-section">
    <div class="container">
        <h2>Why Choose Rise Local?</h2>

        <div class="trust-grid">
            <?php foreach ($benefits as $title => $description): ?>
                <div class="trust-item">
                    <h3><?php echo esc_html($title); ?></h3>
                    <p><?php echo esc_html($description); ?></p>
                </div>
            <?php endforeach; ?>
        </div>
    </div>
</section>

<!-- Service Areas -->
<?php if (!empty($service_areas)): ?>
<section class="stats-section">
    <div class="container text-center">
        <h2 style="margin-bottom: 40px; font-size: 2.5rem; color: #333;">
            Serving Cities Across Texas
        </h2>

        <div class="stats-grid">
            <?php foreach (array_slice($service_areas, 0, 12) as $area): ?>
                <div class="stat-card">
                    <h3 style="font-size: 1.2rem; margin-bottom: 10px;">
                        <a href="<?php echo esc_url(home_url('/electricians/' . sanitize_title($area) . '/')); ?>" style="color: #667eea; text-decoration: none;">
                            <?php echo esc_html($area); ?>
                        </a>
                    </h3>
                    <p style="color: #666; font-size: 0.9rem;">Find Electricians</p>
                </div>
            <?php endforeach; ?>
        </div>
    </div>
</section>
<?php endif; ?>

<!-- Pain Points / CTA Section -->
<section class="container" style="padding: 80px 20px; max-width: 900px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 60px 40px; border-radius: 16px; color: white; text-align: center;">
        <h2 style="font-size: 2.5rem; margin-bottom: 30px;">Ready to Grow Your Electrical Business?</h2>

        <p style="font-size: 1.2rem; margin-bottom: 40px; opacity: 0.95;">
            Join our network of verified electricians and get connected with customers actively searching for your services.
        </p>

        <ul style="list-style: none; padding: 0; margin: 0 0 40px; text-align: left; max-width: 500px; margin-left: auto; margin-right: auto;">
            <?php foreach ($pain_points as $point): ?>
                <li style="margin-bottom: 15px; padding-left: 30px; position: relative;">
                    <span style="position: absolute; left: 0; top: 0; font-size: 1.2rem;">✓</span>
                    <?php echo esc_html($point); ?>
                </li>
            <?php endforeach; ?>
        </ul>

        <a href="#lead-form" class="btn-submit" style="display: inline-block; background: white; color: #667eea; text-decoration: none; max-width: 300px;">
            Get Started Now
        </a>
    </div>
</section>

<!-- Footer -->
<footer class="site-footer">
    <div class="container">
        <p>&copy; <?php echo date('Y'); ?> Rise Local. All rights reserved.</p>
        <p>Connecting Texas businesses with qualified electricians since 2024.</p>
    </div>
</footer>

<?php wp_footer(); ?>

</body>
</html>
