"""
Data models for the Rise Local Pipeline
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum


class QualificationStatus(Enum):
    REJECTED = "rejected"
    MARGINAL = "marginal"
    QUALIFIED = "qualified"


class LeadStatus(Enum):
    NEW = "new"
    PROCESSING = "processing"
    QUALIFIED = "qualified"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"
    DELIVERED = "delivered"
    FAILED = "failed"


class LeadCategory(Enum):
    """
    Lead categories for personalized email/landing page routing.
    Assigned during pre-qualification using FREE data sources.
    """
    THE_INVISIBLE = "the_invisible"         # No/minimal online presence
    THE_DIY_CEILING = "the_diy_ceiling"     # Built own site, hit growth limit
    THE_LEAKY_BUCKET = "the_leaky_bucket"   # Traffic but poor conversion
    THE_OVERWHELMED = "the_overwhelmed"     # Growing fast, need systems
    READY_TO_DOMINATE = "ready_to_dominate" # Has basics, wants to scale
    UNCATEGORIZED = "uncategorized"         # Doesn't fit clear category


@dataclass
class Lead:
    """Lead data from Supabase"""
    id: str
    business_name: str
    address: str = ""
    city: str = ""
    state: str = "TX"
    zip_code: str = ""
    phone: str = ""
    website_url: str = ""
    google_rating: float = 0.0
    review_count: int = 0
    place_id: str = ""
    status: str = "new"


@dataclass
class TechEnrichment:
    """Tech stack data from Clay/BuiltWith with AI analysis"""
    # Raw BuiltWith data from Clay
    tech_raw_list: str = ""  # Comma-separated technology list
    tech_count: int = 0  # Total number of technologies

    # Legacy boolean fields (kept for backward compatibility)
    has_gtm: bool = False
    has_ga4: bool = False
    has_ga_universal: bool = False
    has_crm: bool = False
    has_booking_system: bool = False
    has_email_marketing: bool = False
    has_lead_capture: bool = False
    has_chat_widget: bool = False

    # Legacy string fields
    crm_detected: str = ""
    booking_system: str = ""
    cms_platform: str = ""
    email_marketing: str = ""
    chat_widget: str = ""
    tech_score: int = 0
    technologies: List[str] = field(default_factory=list)

    # AI Tech Analysis fields (from Claude Haiku)
    tech_analysis: Optional[Dict] = None  # Full AI response JSONB
    tech_stack_ai_score: int = 0  # 0-10 scale (lower = more pain)
    website_type: str = ""  # "DIY Builder", "Professional", "Outdated WordPress", etc.
    cms_platform_ai: str = ""  # AI's detected CMS
    tech_analysis_model: str = ""  # e.g., "claude-3-5-haiku-20241022"
    tech_analysis_at: str = ""  # ISO timestamp


@dataclass
class VisualAnalysis:
    """Visual analysis from screenshot service"""
    visual_score: int = 50
    design_era: str = "Unknown"
    mobile_responsive: bool = True
    social_facebook: str = ""
    social_instagram: str = ""
    social_linkedin: str = ""
    trust_signals: int = 0
    has_hero_image: bool = False
    has_clear_cta: bool = False


@dataclass
class TrackingAnalysis:
    """
    FREE tracking/tech detection from HTML inspection.
    Collected by Screenshot Service during visual analysis.
    Used in pre-qualification BEFORE Clay enrichment.
    """
    # Analytics (FREE detection)
    has_gtm: bool = False
    has_ga4: bool = False
    has_ga_universal: bool = False
    has_facebook_pixel: bool = False
    has_hotjar: bool = False

    # Chat Widgets
    has_chat_widget: bool = False
    chat_provider: Optional[str] = None  # intercom, drift, crisp, tawk, etc.

    # Booking Systems
    has_booking: bool = False
    booking_provider: Optional[str] = None  # calendly, housecall_pro, jobber, etc.

    # CRM/Marketing
    has_crm: bool = False
    crm_provider: Optional[str] = None  # hubspot, salesforce, zoho, etc.
    has_email_marketing: bool = False
    email_provider: Optional[str] = None  # mailchimp, klaviyo, etc.

    # CMS Detection (FREE - from HTML signatures)
    cms_detected: Optional[str] = None  # WordPress, Wix, Squarespace, etc.

    # Lead Capture Forms
    has_lead_capture_form: bool = False
    has_contact_form: bool = False


@dataclass
class TechnicalScores:
    """PageSpeed/technical analysis"""
    performance_score: int = 50
    mobile_score: int = 50
    seo_score: int = 50
    accessibility_score: int = 50
    has_https: bool = True
    lcp_ms: int = 0
    fid_ms: int = 0
    cls: float = 0.0


@dataclass
class DirectoryPresence:
    """Yext directory/listings data"""
    listings_score: int = 50
    listings_found: int = 0
    listings_verified: int = 0
    nap_consistency: float = 1.0
    scan_id: str = ""


@dataclass
class LicenseInfo:
    """TDLR license verification"""
    license_status: str = "Unknown"
    owner_name: str = ""
    license_number: str = ""
    license_type: str = ""
    expiry_date: str = ""


@dataclass
class ReputationData:
    """BBB reputation data"""
    bbb_rating: str = "NR"
    bbb_accredited: bool = False
    complaints_3yr: int = 0
    complaints_total: int = 0
    reputation_gap: float = 0.0
    years_in_business: int = 0


@dataclass
class AddressVerification:
    """Address verification (residential vs commercial)"""
    is_residential: bool = False
    address_type: str = "unknown"  # residential, commercial, or unknown
    verified: bool = False
    formatted_address: str = ""


@dataclass
class OwnerExtraction:
    """Owner info extracted from website (for TDLR waterfall)"""
    owner_first_name: str = ""
    owner_last_name: str = ""
    owner_full_name: str = ""
    license_number: str = ""  # TECL license if displayed on website
    email: str = ""
    phone: str = ""
    confidence: str = "low"  # low, medium, high
    extraction_method: str = ""
    error: str = ""


@dataclass
class PainSignal:
    """Individual pain signal"""
    signal: str
    points: int
    category: str


@dataclass
class CategoryAssignment:
    """Result of lead categorization for personalized outreach"""
    category: LeadCategory
    reason: str  # Brief explanation of why this category
    confidence: str = "high"  # high, medium, low
    secondary_category: Optional[LeadCategory] = None  # If lead fits multiple


@dataclass
class PainScore:
    """Pain point scoring results"""
    score: int = 0
    signals: List[PainSignal] = field(default_factory=list)
    status: QualificationStatus = QualificationStatus.REJECTED
    top_pain_points: List[str] = field(default_factory=list)
    icp_score: int = 100
    proceed: bool = False


@dataclass
class ContactInfo:
    """Contact enrichment from Clay"""
    owner_email: str = ""
    owner_first_name: str = ""
    owner_last_name: str = ""
    owner_linkedin: str = ""
    owner_phone_direct: str = ""
    email_verified: bool = False
    contact_source: str = ""


@dataclass
class GeneratedEmail:
    """LLM-generated email"""
    subject_line: str = ""
    preview_text: str = ""
    email_body: str = ""
    personalization_hooks: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    valid: bool = False
    error: str = ""
    word_count: int = 0


@dataclass
class PipelineResult:
    """Final pipeline result"""
    lead_id: str
    status: LeadStatus
    qualification_status: Optional[QualificationStatus] = None
    pain_score: int = 0
    icp_score: int = 0
    email_subject: str = ""
    ab_variant: str = ""
    owner_email: str = ""
    error: Optional[str] = None

    # Lead category for personalized outreach
    lead_category: Optional[LeadCategory] = None
    category_reason: str = ""

    # All collected data for storage
    tech_enrichment: Optional[TechEnrichment] = None
    visual_analysis: Optional[VisualAnalysis] = None
    tracking_analysis: Optional[TrackingAnalysis] = None  # FREE tracking data
    technical_scores: Optional[TechnicalScores] = None
    directory_presence: Optional[DirectoryPresence] = None
    license_info: Optional[LicenseInfo] = None
    reputation_data: Optional[ReputationData] = None
    address_verification: Optional[AddressVerification] = None
    contact_info: Optional[ContactInfo] = None
    generated_email: Optional[GeneratedEmail] = None
    category_assignment: Optional[CategoryAssignment] = None
