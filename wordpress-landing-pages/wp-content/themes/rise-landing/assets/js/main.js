/**
 * Rise Landing Pages - Main JavaScript
 * @version 1.0.0
 */

(function($) {
    'use strict';

    // Document ready
    $(document).ready(function() {
        initFormHandler();
        initSmoothScroll();
        initPhoneFormatting();
    });

    /**
     * Initialize form submission handler
     */
    function initFormHandler() {
        const $form = $('#lead-form');

        if (!$form.length) {
            return;
        }

        $form.on('submit', function(e) {
            e.preventDefault();

            // Get form data
            const formData = $(this).serialize();

            // Add nonce and action
            const submitData = formData + '&action=submit_lead_form&nonce=' + riseAjax.nonce;

            // Get submit button
            const $submitBtn = $(this).find('.btn-submit');
            const originalText = $submitBtn.text();

            // Disable button and show loading
            $submitBtn
                .text('Submitting...')
                .prop('disabled', true);

            // Clear any previous messages
            $('.form-message').remove();

            // Submit via AJAX
            $.ajax({
                url: riseAjax.ajaxurl,
                type: 'POST',
                data: submitData,
                dataType: 'json',
                success: function(response) {
                    if (response.success) {
                        // Show success message
                        showFormMessage('success', response.data.message);

                        // Reset form
                        $form[0].reset();

                        // Redirect if URL provided
                        if (response.data.redirect) {
                            setTimeout(function() {
                                window.location.href = response.data.redirect;
                            }, 2000);
                        }
                    } else {
                        // Show error message
                        showFormMessage('error', response.data.message || 'Something went wrong. Please try again.');
                    }
                },
                error: function(xhr, status, error) {
                    console.error('Form submission error:', error);
                    showFormMessage('error', 'Network error. Please check your connection and try again.');
                },
                complete: function() {
                    // Re-enable button
                    $submitBtn
                        .text(originalText)
                        .prop('disabled', false);
                }
            });
        });
    }

    /**
     * Show form message
     */
    function showFormMessage(type, message) {
        const $form = $('#lead-form');
        const className = type === 'success' ? 'success-message' : 'error-message';

        const $message = $('<div>')
            .addClass('form-message ' + className)
            .html(message);

        $form.prepend($message);

        // Auto-hide after 10 seconds
        setTimeout(function() {
            $message.fadeOut(function() {
                $(this).remove();
            });
        }, 10000);

        // Scroll to message
        $('html, body').animate({
            scrollTop: $message.offset().top - 100
        }, 500);
    }

    /**
     * Initialize smooth scrolling for anchor links
     */
    function initSmoothScroll() {
        $('a[href^="#"]').on('click', function(e) {
            const target = $(this.getAttribute('href'));

            if (target.length) {
                e.preventDefault();

                $('html, body').stop().animate({
                    scrollTop: target.offset().top - 80
                }, 800);
            }
        });
    }

    /**
     * Initialize phone number formatting
     */
    function initPhoneFormatting() {
        const $phoneInput = $('#phone');

        if (!$phoneInput.length) {
            return;
        }

        $phoneInput.on('input', function() {
            let value = $(this).val().replace(/\D/g, '');

            // Limit to 10 digits
            if (value.length > 10) {
                value = value.substr(0, 10);
            }

            // Format as (XXX) XXX-XXXX
            if (value.length >= 6) {
                value = '(' + value.substr(0, 3) + ') ' + value.substr(3, 3) + '-' + value.substr(6);
            } else if (value.length >= 3) {
                value = '(' + value.substr(0, 3) + ') ' + value.substr(3);
            }

            $(this).val(value);
        });
    }

    /**
     * Initialize card animations on scroll
     */
    function initScrollAnimations() {
        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver(function(entries) {
                entries.forEach(function(entry) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('visible');
                    }
                });
            }, {
                threshold: 0.1
            });

            document.querySelectorAll('.business-card, .stat-card, .trust-item').forEach(function(card) {
                observer.observe(card);
            });
        }
    }

    // Initialize animations on load
    $(window).on('load', function() {
        initScrollAnimations();
    });

})(jQuery);
