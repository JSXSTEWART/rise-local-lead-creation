<?php
/**
 * Dynamic Content Helpers
 * Utility functions for generating dynamic landing page content
 *
 * @package RiseLanding
 * @version 1.0.0
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

/**
 * Generate pain points for a category
 *
 * @param string $category Category name
 * @return array Pain points
 */
function rise_get_category_pain_points($category) {
    $pain_points = [
        'electricians' => [
            'Outdated website that doesn\'t showcase your expertise',
            'Not showing up in local Google searches',
            'Losing leads to competitors with better online presence',
            'No online booking or contact system',
            'Missing out on Google reviews and reputation building'
        ],
        'plumbers' => [
            'Customers can\'t find you online for emergency services',
            'Website doesn\'t work well on mobile phones',
            'No way to collect reviews or showcase testimonials',
            'Competitors rank higher in local searches',
            'Missing opportunities from 24/7 online lead generation'
        ],
        'hvac' => [
            'Seasonal demand fluctuations hurt your bottom line',
            'Outdated marketing materials don\'t convert',
            'Can\'t track ROI on advertising spend',
            'Losing commercial contracts to better-marketed competitors',
            'No system for customer retention and maintenance contracts'
        ],
        'contractors' => [
            'Portfolio isn\'t showcased effectively online',
            'Difficult to explain complex services to prospects',
            'No way to generate estimates or quotes online',
            'Missing out on high-value commercial projects',
            'Lack of professional online presence hurts credibility'
        ]
    ];

    return $pain_points[$category] ?? [
        'Not enough qualified leads coming in',
        'Outdated or missing online presence',
        'Losing business to competitors',
        'Difficult to track marketing ROI',
        'No system for customer retention'
    ];
}

/**
 * Generate benefits for a category
 *
 * @param string $category Category name
 * @return array Benefits
 */
function rise_get_category_benefits($category) {
    $benefits = [
        'electricians' => [
            '✅ Licensed & Insured' => 'All electricians are verified and carry proper insurance',
            '⚡ Fast Response' => 'Get quotes from 3 electricians within 24 hours',
            '🏆 Top Rated' => 'Only 4+ star rated businesses with positive reviews',
            '💯 Free Service' => 'Completely free for homeowners and businesses'
        ],
        'plumbers' => [
            '✅ Certified Plumbers' => 'Licensed professionals with years of experience',
            '🚰 Emergency Service' => 'Find 24/7 emergency plumbers in your area',
            '⭐ Verified Reviews' => 'Real customer reviews and ratings',
            '💰 Free Quotes' => 'Compare multiple quotes at no cost'
        ],
        'hvac' => [
            '❄️ Certified Technicians' => 'EPA-certified HVAC professionals',
            '🔧 Full Service' => 'Installation, repair, and maintenance',
            '💼 Commercial & Residential' => 'Serving both business and home needs',
            '💯 No Obligation' => 'Free quotes, no commitment required'
        ],
        'contractors' => [
            '🏗️ Licensed Contractors' => 'Verified general contractors in your area',
            '📋 Detailed Estimates' => 'Get comprehensive project quotes',
            '🏆 Proven Track Record' => 'Reviews and completed project portfolios',
            '💯 Free Matching' => 'No cost to find the right contractor'
        ]
    ];

    return $benefits[$category] ?? [
        '✅ Verified Professionals' => 'All businesses are pre-screened and verified',
        '⚡ Fast Matching' => 'Connect with 3 pros within 24 hours',
        '⭐ Top Rated' => 'Only highly-rated businesses with positive reviews',
        '💯 Free Service' => 'Completely free for customers'
    ];
}

/**
 * Generate FAQ content for a category
 *
 * @param string $category Category name
 * @return array FAQs
 */
function rise_get_category_faqs($category) {
    $faqs = [
        'electricians' => [
            [
                'question' => 'How quickly can I get quotes from electricians?',
                'answer' => 'Most customers receive quotes from 3 pre-screened electricians within 24 hours of submitting their information.'
            ],
            [
                'question' => 'Are all electricians licensed and insured?',
                'answer' => 'Yes, we only work with licensed electricians who carry proper insurance and have verified credentials.'
            ],
            [
                'question' => 'Is there any cost to use this service?',
                'answer' => 'No, our service is completely free for customers. Electricians pay us a small fee to be part of our network.'
            ],
            [
                'question' => 'What areas do you cover?',
                'answer' => 'We currently serve all major cities across Texas, including Austin, Houston, Dallas, San Antonio, and more.'
            ]
        ]
    ];

    return $faqs[$category] ?? [];
}

/**
 * Get service areas for a category
 *
 * @param string $category Category name
 * @return array Cities
 */
function rise_get_service_areas($category = null) {
    // Get from Supabase stats
    $supabase = rise_supabase();

    if ($category && $supabase->is_configured()) {
        $stats = $supabase->get_category_stats($category);
        if (!empty($stats['cities'])) {
            return $stats['cities'];
        }
    }

    // Fallback to static list
    return [
        'Austin', 'Houston', 'Dallas', 'San Antonio', 'Fort Worth',
        'El Paso', 'Arlington', 'Corpus Christi', 'Plano', 'Lubbock',
        'Irving', 'Laredo', 'Garland', 'Frisco', 'McKinney'
    ];
}

/**
 * Format business hours
 *
 * @param array $hours Business hours data
 * @return string Formatted hours
 */
function rise_format_business_hours($hours) {
    if (empty($hours) || !is_array($hours)) {
        return 'Call for hours';
    }

    // Simple formatting - could be enhanced
    return 'Mon-Fri: 8am-6pm';
}

/**
 * Generate structured data (JSON-LD) for SEO
 *
 * @param string $category Category name
 * @param array $business Business data (optional)
 * @return string JSON-LD markup
 */
function rise_generate_structured_data($category, $business = null) {
    $data = [
        '@context' => 'https://schema.org',
        '@type' => 'ProfessionalService',
        'name' => 'Rise Local - Find ' . rise_get_category_display_name($category),
        'description' => 'Find pre-qualified, top-rated ' . strtolower(rise_get_category_display_name($category)) . ' in Texas',
        'url' => home_url('/' . $category . '/'),
        'areaServed' => [
            '@type' => 'State',
            'name' => 'Texas'
        ]
    ];

    if ($business) {
        $data = [
            '@context' => 'https://schema.org',
            '@type' => 'LocalBusiness',
            'name' => $business['business_name'] ?? '',
            'telephone' => $business['phone'] ?? '',
            'address' => [
                '@type' => 'PostalAddress',
                'streetAddress' => $business['address_street'] ?? '',
                'addressLocality' => $business['address_city'] ?? '',
                'addressRegion' => $business['address_state'] ?? 'TX',
                'postalCode' => $business['address_zip'] ?? ''
            ]
        ];

        if (!empty($business['google_rating'])) {
            $data['aggregateRating'] = [
                '@type' => 'AggregateRating',
                'ratingValue' => $business['google_rating'],
                'reviewCount' => $business['google_review_count'] ?? 0
            ];
        }
    }

    return '<script type="application/ld+json">' . json_encode($data, JSON_UNESCAPED_SLASHES) . '</script>';
}
