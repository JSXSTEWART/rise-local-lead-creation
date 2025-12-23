<?php
/**
 * Supabase Client for WordPress
 * Connects to Supabase PostgreSQL database via REST API
 *
 * @package RiseLanding
 * @version 1.0.0
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

class Rise_Supabase_Client {
    private $base_url;
    private $api_key;
    private $headers;

    public function __construct() {
        $this->base_url = defined('SUPABASE_URL') ? SUPABASE_URL . '/rest/v1' : '';
        $this->api_key = defined('SUPABASE_KEY') ? SUPABASE_KEY : '';

        $this->headers = [
            'apikey' => $this->api_key,
            'Authorization' => 'Bearer ' . $this->api_key,
            'Content-Type' => 'application/json',
            'Prefer' => 'return=representation'
        ];
    }

    /**
     * Get leads by category
     *
     * @param string $category Category filter (optional)
     * @param int $limit Number of results
     * @param array $filters Additional filters
     * @return array Array of leads
     */
    public function get_leads_by_category($category = null, $limit = 10, $filters = []) {
        if (empty($this->base_url) || empty($this->api_key)) {
            error_log('Supabase credentials not configured');
            return [];
        }

        $url = $this->base_url . '/leads';
        $query_params = [];

        // Status filter
        $query_params[] = 'status=eq.qualified';

        // Category filter (optional)
        if ($category) {
            $query_params[] = 'category=ilike.*' . urlencode($category) . '*';
        }

        // City filter (optional)
        if (!empty($filters['city'])) {
            $query_params[] = 'address_city=ilike.*' . urlencode($filters['city']) . '*';
        }

        // State filter
        $query_params[] = 'address_state=eq.' . urlencode($filters['state'] ?? 'TX');

        // Limit and order
        $query_params[] = 'limit=' . intval($limit);
        $query_params[] = 'order=google_rating.desc.nullslast,created_at.desc';

        // Build final URL
        $url .= '?' . implode('&', $query_params);

        // Make request
        $response = wp_remote_get($url, [
            'headers' => $this->headers,
            'timeout' => 15
        ]);

        if (is_wp_error($response)) {
            error_log('Supabase API Error: ' . $response->get_error_message());
            return [];
        }

        $code = wp_remote_retrieve_response_code($response);
        if ($code !== 200) {
            error_log('Supabase API returned code: ' . $code);
            return [];
        }

        $body = wp_remote_retrieve_body($response);
        $data = json_decode($body, true);

        return is_array($data) ? $data : [];
    }

    /**
     * Get single business by slug
     *
     * @param string $slug Business slug (e.g., 'abc-electric')
     * @return array|null Business data or null
     */
    public function get_business_by_slug($slug) {
        if (empty($this->base_url) || empty($this->api_key)) {
            return null;
        }

        // Convert slug to business name (abc-electric -> ABC Electric)
        $business_name = ucwords(str_replace('-', ' ', $slug));

        $url = $this->base_url . '/leads';
        $url .= '?business_name=ilike.*' . urlencode($business_name) . '*';
        $url .= '&limit=1';

        $response = wp_remote_get($url, [
            'headers' => $this->headers,
            'timeout' => 15
        ]);

        if (is_wp_error($response)) {
            error_log('Supabase get_business_by_slug error: ' . $response->get_error_message());
            return null;
        }

        $body = wp_remote_retrieve_body($response);
        $data = json_decode($body, true);

        return !empty($data) && is_array($data) ? $data[0] : null;
    }

    /**
     * Create new lead in Supabase
     *
     * @param array $lead_data Lead data
     * @return bool|array Success boolean or created lead data
     */
    public function create_lead($lead_data) {
        if (empty($this->base_url) || empty($this->api_key)) {
            error_log('Supabase credentials not configured');
            return false;
        }

        $url = $this->base_url . '/leads';

        // Ensure required fields
        $lead_data = array_merge([
            'status' => 'new',
            'source' => 'landing_page',
            'created_at' => gmdate('Y-m-d\TH:i:s\Z')
        ], $lead_data);

        $response = wp_remote_post($url, [
            'headers' => $this->headers,
            'body' => json_encode($lead_data),
            'timeout' => 15
        ]);

        if (is_wp_error($response)) {
            error_log('Supabase create_lead error: ' . $response->get_error_message());
            return false;
        }

        $code = wp_remote_retrieve_response_code($response);

        if ($code === 201) {
            $body = wp_remote_retrieve_body($response);
            return json_decode($body, true);
        } else {
            $body = wp_remote_retrieve_body($response);
            error_log('Supabase create_lead failed: ' . $code . ' - ' . $body);
            return false;
        }
    }

    /**
     * Get category statistics
     *
     * @param string $category Category name
     * @return array Statistics
     */
    public function get_category_stats($category) {
        $leads = $this->get_leads_by_category($category, 100);

        $stats = [
            'total_businesses' => count($leads),
            'avg_rating' => 0,
            'total_reviews' => 0,
            'cities' => []
        ];

        if (empty($leads)) {
            return $stats;
        }

        $rating_sum = 0;
        $rating_count = 0;
        $cities = [];

        foreach ($leads as $lead) {
            // Calculate average rating
            if (!empty($lead['google_rating'])) {
                $rating_sum += floatval($lead['google_rating']);
                $rating_count++;
            }

            // Sum reviews
            if (!empty($lead['google_review_count'])) {
                $stats['total_reviews'] += intval($lead['google_review_count']);
            }

            // Collect cities
            if (!empty($lead['address_city'])) {
                $city = $lead['address_city'];
                if (!isset($cities[$city])) {
                    $cities[$city] = 0;
                }
                $cities[$city]++;
            }
        }

        $stats['avg_rating'] = $rating_count > 0 ? round($rating_sum / $rating_count, 1) : 0;

        // Sort cities by count
        arsort($cities);
        $stats['cities'] = array_keys(array_slice($cities, 0, 10));

        return $stats;
    }

    /**
     * Check if Supabase is configured
     *
     * @return bool
     */
    public function is_configured() {
        return !empty($this->base_url) && !empty($this->api_key);
    }
}

/**
 * Global instance getter
 *
 * @return Rise_Supabase_Client
 */
function rise_supabase() {
    static $instance = null;

    if ($instance === null) {
        $instance = new Rise_Supabase_Client();
    }

    return $instance;
}
