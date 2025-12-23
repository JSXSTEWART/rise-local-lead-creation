<?php
/**
 * Rise Landing Pages Theme
 * Main index template (fallback)
 *
 * @package RiseLanding
 * @version 1.0.0
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

get_header();
?>

<!DOCTYPE html>
<html <?php language_attributes(); ?>>
<head>
    <meta charset="<?php bloginfo('charset'); ?>">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php bloginfo('name'); ?> | <?php bloginfo('description'); ?></title>
    <?php wp_head(); ?>
</head>
<body>

<div class="hero">
    <div class="container">
        <h1>🚀 Rise Local Lead Generation</h1>
        <p>Choose a category to get started</p>
    </div>
</div>

<section class="container" style="padding: 60px 20px;">
    <div class="stats-grid">
        <div class="stat-card">
            <h3><a href="<?php echo home_url('/electricians/'); ?>" style="color: #667eea; text-decoration: none;">⚡ Electricians</a></h3>
            <p>Find licensed electricians in Texas</p>
        </div>

        <div class="stat-card">
            <h3><a href="<?php echo home_url('/plumbers/'); ?>" style="color: #667eea; text-decoration: none;">🔧 Plumbers</a></h3>
            <p>Find certified plumbers in Texas</p>
        </div>

        <div class="stat-card">
            <h3><a href="<?php echo home_url('/hvac/'); ?>" style="color: #667eea; text-decoration: none;">❄️ HVAC</a></h3>
            <p>Find HVAC contractors in Texas</p>
        </div>

        <div class="stat-card">
            <h3><a href="<?php echo home_url('/contractors/'); ?>" style="color: #667eea; text-decoration: none;">🏗️ Contractors</a></h3>
            <p>Find general contractors in Texas</p>
        </div>
    </div>
</section>

<footer class="site-footer">
    <div class="container">
        <p>&copy; <?php echo date('Y'); ?> Rise Local. All rights reserved.</p>
    </div>
</footer>

<?php wp_footer(); ?>

</body>
</html>
