// Rise Local - Secure Authentication Layer
// This file handles Supabase authentication and session management

class AuthManager {
    constructor() {
        this.supabase = null;
        this.currentUser = null;
        this.sessionCheckInterval = null;
    }

    /**
     * Initialize Supabase client with credentials from secure config endpoint
     */
    async init() {
        try {
            // Fetch Supabase configuration from secure backend endpoint
            // This prevents exposing credentials in frontend code
            const configResponse = await fetch('/api/config/supabase');

            if (!configResponse.ok) {
                throw new Error('Failed to fetch Supabase configuration');
            }

            const config = await configResponse.json();

            // Initialize Supabase client with fetched credentials
            this.supabase = window.supabase.createClient(config.url, config.anonKey);

            // Check for existing session
            const { data: { session } } = await this.supabase.auth.getSession();

            if (session) {
                this.currentUser = session.user;
                this.startSessionCheck();
                return true;
            }

            return false;
        } catch (error) {
            console.error('Auth initialization error:', error);
            throw error;
        }
    }

    /**
     * Sign in with email and password
     */
    async signIn(email, password) {
        try {
            const { data, error } = await this.supabase.auth.signInWithPassword({
                email,
                password
            });

            if (error) throw error;

            this.currentUser = data.user;
            this.startSessionCheck();

            // Log authentication event
            await this.logAuditEvent('user_login', {
                user_id: this.currentUser.id,
                email: this.currentUser.email
            });

            return { success: true, user: data.user };
        } catch (error) {
            console.error('Sign in error:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Sign out current user
     */
    async signOut() {
        try {
            const userId = this.currentUser?.id;

            await this.supabase.auth.signOut();

            this.currentUser = null;
            this.stopSessionCheck();

            // Log logout event
            if (userId) {
                await this.logAuditEvent('user_logout', { user_id: userId });
            }

            return { success: true };
        } catch (error) {
            console.error('Sign out error:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Get current authenticated user
     */
    getCurrentUser() {
        return this.currentUser;
    }

    /**
     * Check if user is authenticated
     */
    isAuthenticated() {
        return this.currentUser !== null;
    }

    /**
     * Get Supabase client instance
     */
    getClient() {
        return this.supabase;
    }

    /**
     * Start periodic session validity check
     */
    startSessionCheck() {
        // Check session every 5 minutes
        this.sessionCheckInterval = setInterval(async () => {
            const { data: { session } } = await this.supabase.auth.getSession();

            if (!session) {
                // Session expired, redirect to login
                this.stopSessionCheck();
                this.currentUser = null;
                window.location.href = '/login.html';
            }
        }, 5 * 60 * 1000);
    }

    /**
     * Stop session check interval
     */
    stopSessionCheck() {
        if (this.sessionCheckInterval) {
            clearInterval(this.sessionCheckInterval);
            this.sessionCheckInterval = null;
        }
    }

    /**
     * Log audit event to tracking table
     */
    async logAuditEvent(action, metadata) {
        try {
            await this.supabase.from('audit_log').insert({
                timestamp: new Date().toISOString(),
                actor: this.currentUser?.email || 'anonymous',
                actor_type: 'human',
                action: action,
                metadata: metadata
            });
        } catch (error) {
            console.error('Failed to log audit event:', error);
        }
    }

    /**
     * Get user role from database
     */
    async getUserRole() {
        if (!this.currentUser) return null;

        try {
            const { data, error } = await this.supabase
                .from('user_roles')
                .select('role')
                .eq('user_id', this.currentUser.id)
                .single();

            if (error) throw error;
            return data.role;
        } catch (error) {
            console.error('Error fetching user role:', error);
            return 'viewer'; // Default role
        }
    }

    /**
     * Check if user has specific permission
     */
    async hasPermission(permission) {
        const role = await this.getUserRole();

        const permissions = {
            admin: ['read', 'write', 'delete', 'configure', 'override_agents'],
            operator: ['read', 'write', 'configure'],
            viewer: ['read']
        };

        return permissions[role]?.includes(permission) || false;
    }
}

// Create singleton instance
const authManager = new AuthManager();

// Export for use in other scripts
window.authManager = authManager;
