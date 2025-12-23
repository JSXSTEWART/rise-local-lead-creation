<?php
/**
 * Form Handler for Lead Submissions
 * Processes contact form data and submits to Supabase
 *
 * @package RiseLanding
 * @version 1.0.0
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

/**
 * Handle AJAX form submission
 */
function rise_handle_form_submission() {
    // Verify nonce for security
    if (!isset($_POST['nonce']) || !wp_verify_nonce($_POST['nonce'], 'rise_form_submit')) {
        wp_send_json_error([
            'message' => 'Security check failed. Please refresh the page and try again.'
        ]);
        return;
    }

    // Sanitize and validate input
    $business_name = sanitize_text_field($_POST['business_name'] ?? '');
    $contact_name = sanitize_text_field($_POST['contact_name'] ?? '');
    $email = sanitize_email($_POST['email'] ?? '');
    $phone = sanitize_text_field($_POST['phone'] ?? '');
    $website = esc_url_raw($_POST['website'] ?? '');
    $address = sanitize_text_field($_POST['address'] ?? '');
    $city = sanitize_text_field($_POST['city'] ?? '');
    $state = sanitize_text_field($_POST['state'] ?? 'TX');
    $zip = sanitize_text_field($_POST['zip'] ?? '');
    $category = sanitize_text_field($_POST['category'] ?? 'general');
    $message = sanitize_textarea_field($_POST['message'] ?? '');

    // Validate required fields
    $errors = [];

    if (empty($business_name)) {
        $errors[] = 'Business name is required';
    }

    if (empty($contact_name)) {
        $errors[] = 'Contact name is required';
    }

    if (empty($email)) {
        $errors[] = 'Email is required';
    } elseif (!is_email($email)) {
        $errors[] = 'Please enter a valid email address';
    }

    if (empty($phone)) {
        $errors[] = 'Phone number is required';
    }

    if (empty($city)) {
        $errors[] = 'City is required';
    }

    // Return validation errors
    if (!empty($errors)) {
        wp_send_json_error([
            'message' => implode('. ', $errors) . '.'
        ]);
        return;
    }

    // Prepare lead data for Supabase
    $lead_data = [
        'business_name' => $business_name,
        'owner_name' => $contact_name,
        'owner_email' => $email,
        'phone' => rise_format_phone($phone),
        'website' => $website,
        'address_full' => $address,
        'address_city' => $city,
        'address_state' => strtoupper($state),
        'address_zip' => $zip,
        'status' => 'new',
        'source' => 'landing_page_' . $category,
        'created_at' => gmdate('Y-m-d\TH:i:s\Z'),
        'metadata' => json_encode([
            'form_category' => $category,
            'message' => $message,
            'user_agent' => $_SERVER['HTTP_USER_AGENT'] ?? '',
            'ip_address' => rise_get_client_ip(),
            'submitted_at' => current_time('mysql')
        ])
    ];

    // Submit to Supabase
    $supabase = rise_supabase();

    if (!$supabase->is_configured()) {
        error_log('Rise Landing: Supabase not configured');
        wp_send_json_error([
            'message' => 'System error. Please contact support.'
        ]);
        return;
    }

    $result = $supabase->create_lead($lead_data);

    if ($result) {
        // Success - send notification email to admin
        rise_send_admin_notification($lead_data);

        // Success response
        wp_send_json_success([
            'message' => 'Thank you! Your information has been submitted. We\'ll be in touch within 24 hours.',
            'redirect' => home_url('/thank-you/')
        ]);
    } else {
        // Error response
        error_log('Rise Landing: Failed to create lead in Supabase');
        wp_send_json_error([
            'message' => 'Something went wrong. Please try again or call us directly.'
        ]);
    }
}

/**
 * Send admin notification email
 *
 * @param array $lead_data Lead data
 */
function rise_send_admin_notification($lead_data) {
    $to = get_option('admin_email');
    $subject = 'New Lead from Landing Page: ' . $lead_data['business_name'];

    $message = "New lead submitted from Rise Landing Page\n\n";
    $message .= "Business: {$lead_data['business_name']}\n";
    $message .= "Contact: {$lead_data['owner_name']}\n";
    $message .= "Email: {$lead_data['owner_email']}\n";
    $message .= "Phone: {$lead_data['phone']}\n";
    $message .= "City: {$lead_data['address_city']}, {$lead_data['address_state']}\n";
    $message .= "Source: {$lead_data['source']}\n\n";

    if (!empty($lead_data['website'])) {
        $message .= "Website: {$lead_data['website']}\n";
    }

    $metadata = json_decode($lead_data['metadata'], true);
    if (!empty($metadata['message'])) {
        $message .= "\nMessage:\n{$metadata['message']}\n";
    }

    $message .= "\nSubmitted: {$metadata['submitted_at']}\n";
    $message .= "IP: {$metadata['ip_address']}\n";

    $headers = [
        'Content-Type: text/plain; charset=UTF-8',
        'From: Rise Landing <noreply@' . parse_url(home_url(), PHP_URL_HOST) . '>'
    ];

    wp_mail($to, $subject, $message, $headers);
}

/**
 * Format phone number
 *
 * @param string $phone Raw phone number
 * @return string Formatted phone number
 */
function rise_format_phone($phone) {
    // Remove all non-numeric characters
    $phone = preg_replace('/[^0-9]/', '', $phone);

    // Format as (XXX) XXX-XXXX if 10 digits
    if (strlen($phone) === 10) {
        return sprintf('(%s) %s-%s',
            substr($phone, 0, 3),
            substr($phone, 3, 3),
            substr($phone, 6)
        );
    }

    return $phone;
}

/**
 * Get client IP address
 *
 * @return string IP address
 */
function rise_get_client_ip() {
    $ip = '';

    if (!empty($_SERVER['HTTP_CLIENT_IP'])) {
        $ip = $_SERVER['HTTP_CLIENT_IP'];
    } elseif (!empty($_SERVER['HTTP_X_FORWARDED_FOR'])) {
        $ip = $_SERVER['HTTP_X_FORWARDED_FOR'];
    } else {
        $ip = $_SERVER['REMOTE_ADDR'] ?? '';
    }

    return sanitize_text_field($ip);
}
