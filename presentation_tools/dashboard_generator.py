"""
Rise Local Sales Deck Generator

Question-driven workflow that gathers context and generates
Nano Banana prompts for creating a professional sales deck.

Usage:
    python dashboard_generator.py              # Interactive mode
    python dashboard_generator.py --export     # Export prompts to file
"""
import json
from typing import Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DeckContext:
    """Context gathered from question operation."""
    company_name: str = "Rise Local"
    tagline: str = ""
    target_audience: str = ""
    main_problem: str = ""
    key_solutions: List[str] = field(default_factory=list)
    unique_value: str = ""
    results_stats: Dict[str, str] = field(default_factory=dict)
    packages: List[Dict[str, str]] = field(default_factory=list)
    cta_action: str = ""
    visual_style: str = "modern"
    color_scheme: str = "blue"
    slide_count: int = 8


class QuestionOperation:
    """
    Structured question flow to gather sales deck context.

    Each question builds on previous answers for a smooth flow.
    """

    def __init__(self):
        self.context = DeckContext()
        self.questions = self._build_questions()

    def _build_questions(self) -> List[Dict[str, Any]]:
        """Define the question flow."""
        return [
            {
                "id": "target_audience",
                "question": "Who is the primary audience for this sales deck?",
                "options": [
                    "Local service business owners (electricians, plumbers, HVAC)",
                    "Marketing agencies looking to white-label",
                    "Investors/Partners",
                    "Custom (describe)"
                ],
                "field": "target_audience"
            },
            {
                "id": "main_problem",
                "question": "What's the #1 problem we solve for them?",
                "options": [
                    "They're invisible online - losing customers to competitors",
                    "Wasting money on marketing that doesn't work",
                    "No time to manage their online presence",
                    "Custom (describe)"
                ],
                "field": "main_problem"
            },
            {
                "id": "key_solutions",
                "question": "Which solutions should we highlight? (Pick top 3)",
                "multi_select": True,
                "options": [
                    "AI-powered lead qualification",
                    "Automated outreach (email + LinkedIn)",
                    "Website & SEO optimization",
                    "Review management & reputation",
                    "Local directory listings",
                    "Performance analytics dashboard"
                ],
                "field": "key_solutions"
            },
            {
                "id": "unique_value",
                "question": "What makes Rise Local different from competitors?",
                "options": [
                    "10-point pain scoring system finds leads others miss",
                    "AI writes personalized emails that actually convert",
                    "Multi-channel approach (email + LinkedIn + retargeting)",
                    "Custom (describe)"
                ],
                "field": "unique_value"
            },
            {
                "id": "results",
                "question": "What results/stats should we showcase?",
                "type": "key_value",
                "suggested": {
                    "response_rate": "23%",
                    "qualified_leads_per_month": "50+",
                    "time_saved_hours": "40 hrs/week",
                    "avg_deal_value": "$5,000"
                },
                "field": "results_stats"
            },
            {
                "id": "packages",
                "question": "What packages/pricing tiers to include?",
                "type": "multi_entry",
                "suggested": [
                    {"name": "Starter", "price": "$497/mo", "leads": "25 leads"},
                    {"name": "Growth", "price": "$997/mo", "leads": "50 leads"},
                    {"name": "Scale", "price": "$1,997/mo", "leads": "100+ leads"}
                ],
                "field": "packages"
            },
            {
                "id": "cta",
                "question": "What action should the deck drive?",
                "options": [
                    "Book a demo call",
                    "Start free trial",
                    "Schedule strategy session",
                    "Get custom quote"
                ],
                "field": "cta_action"
            },
            {
                "id": "visual_style",
                "question": "Visual style preference?",
                "options": [
                    "Modern minimal (clean, lots of whitespace)",
                    "Bold & vibrant (bright colors, dynamic)",
                    "Corporate professional (traditional, trustworthy)",
                    "Tech-forward (gradients, dark mode)"
                ],
                "field": "visual_style"
            },
            {
                "id": "color_scheme",
                "question": "Primary color scheme?",
                "options": [
                    "Blue (trust, professional)",
                    "Green (growth, success)",
                    "Orange (energy, action)",
                    "Purple (innovation, premium)",
                    "Dark/Charcoal (modern, sophisticated)"
                ],
                "field": "color_scheme"
            }
        ]

    def run_interactive(self) -> DeckContext:
        """Run question operation interactively."""
        print("\n" + "=" * 60)
        print("RISE LOCAL SALES DECK GENERATOR")
        print("Answer these questions to generate your deck prompts")
        print("=" * 60 + "\n")

        for i, q in enumerate(self.questions, 1):
            print(f"\n[{i}/{len(self.questions)}] {q['question']}\n")

            if q.get('options'):
                for j, opt in enumerate(q['options'], 1):
                    print(f"  {j}. {opt}")

                if q.get('multi_select'):
                    print("\n  (Enter numbers separated by commas, e.g., 1,2,3)")
                    response = input("\n  Your choice(s): ").strip()
                    indices = [int(x.strip()) - 1 for x in response.split(',') if x.strip().isdigit()]
                    values = [q['options'][i] for i in indices if i < len(q['options'])]
                    setattr(self.context, q['field'], values)
                else:
                    response = input("\n  Your choice (number or custom text): ").strip()
                    if response.isdigit() and int(response) <= len(q['options']):
                        value = q['options'][int(response) - 1]
                    else:
                        value = response
                    setattr(self.context, q['field'], value)

            elif q.get('type') == 'key_value':
                print("  Suggested values (press Enter to accept, or type new value):")
                values = {}
                for key, suggested in q['suggested'].items():
                    user_input = input(f"    {key} [{suggested}]: ").strip()
                    values[key] = user_input if user_input else suggested
                setattr(self.context, q['field'], values)

            elif q.get('type') == 'multi_entry':
                print("  Suggested packages (press Enter to accept defaults, or 'c' to customize):")
                for pkg in q['suggested']:
                    print(f"    - {pkg['name']}: {pkg['price']} ({pkg['leads']})")

                response = input("\n  Accept defaults? (Enter/c): ").strip().lower()
                if response == 'c':
                    packages = []
                    while True:
                        name = input("  Package name (or 'done'): ").strip()
                        if name.lower() == 'done':
                            break
                        price = input("  Price: ").strip()
                        leads = input("  Leads included: ").strip()
                        packages.append({"name": name, "price": price, "leads": leads})
                    setattr(self.context, q['field'], packages)
                else:
                    setattr(self.context, q['field'], q['suggested'])

        print("\n" + "=" * 60)
        print("Context gathered! Generating prompts...")
        print("=" * 60)

        return self.context

    def get_context_for_api(self) -> Dict[str, Any]:
        """Return context as dict for API/programmatic use."""
        return {
            "company_name": self.context.company_name,
            "tagline": self.context.tagline,
            "target_audience": self.context.target_audience,
            "main_problem": self.context.main_problem,
            "key_solutions": self.context.key_solutions,
            "unique_value": self.context.unique_value,
            "results_stats": self.context.results_stats,
            "packages": self.context.packages,
            "cta_action": self.context.cta_action,
            "visual_style": self.context.visual_style,
            "color_scheme": self.context.color_scheme
        }


class NanoBananaPromptGenerator:
    """
    Generates optimized prompts for Nano Banana Pro.

    Creates a system prompt for Google AI Studio and
    individual slide prompts for the deck.
    """

    SLIDE_TEMPLATES = {
        "title": {
            "name": "Title Slide",
            "purpose": "Hook attention, establish brand",
            "elements": ["Company logo/name", "Tagline", "Visual metaphor"]
        },
        "problem": {
            "name": "Problem Statement",
            "purpose": "Create urgency, relate to pain",
            "elements": ["Statistics", "Pain visualization", "Emotional hook"]
        },
        "solution": {
            "name": "Solution Overview",
            "purpose": "Introduce the answer",
            "elements": ["Key benefits", "Simple diagram", "Before/After"]
        },
        "how_it_works": {
            "name": "How It Works",
            "purpose": "Build understanding",
            "elements": ["Process steps", "Pipeline diagram", "Icons"]
        },
        "features": {
            "name": "Key Features",
            "purpose": "Showcase capabilities",
            "elements": ["Feature icons", "Brief descriptions", "Visual hierarchy"]
        },
        "results": {
            "name": "Results & Proof",
            "purpose": "Build credibility",
            "elements": ["Statistics", "Charts/graphs", "Testimonials"]
        },
        "pricing": {
            "name": "Pricing Packages",
            "purpose": "Present options clearly",
            "elements": ["Tier comparison", "Feature list", "Highlighted recommended"]
        },
        "cta": {
            "name": "Call to Action",
            "purpose": "Drive next step",
            "elements": ["Clear CTA button", "Contact info", "Urgency element"]
        }
    }

    def __init__(self, context: DeckContext):
        self.context = context

    def generate_system_prompt(self) -> str:
        """Generate the master system prompt for Google AI Studio."""
        return f'''You are an expert presentation designer creating slides for Nano Banana Pro.

BRAND CONTEXT:
- Company: {self.context.company_name}
- Target Audience: {self.context.target_audience}
- Visual Style: {self.context.visual_style}
- Color Scheme: {self.context.color_scheme}

DESIGN PRINCIPLES:
1. Clean, professional layouts with clear visual hierarchy
2. Use the {self.context.color_scheme} color as primary, with complementary accents
3. Minimal text - let visuals tell the story
4. Include relevant icons and infographics
5. Ensure text is large and legible
6. Leave breathing room (whitespace)

CONTENT GUIDELINES:
- Problem: {self.context.main_problem}
- Solutions: {", ".join(self.context.key_solutions[:3]) if self.context.key_solutions else "AI-powered lead generation"}
- Differentiator: {self.context.unique_value}
- CTA: {self.context.cta_action}

When generating slide images:
- Create as professional infographic/presentation slide
- Include placeholder areas for text that will be added later
- Use visual metaphors relevant to local business marketing
- Style: {self.context.visual_style}

Output format: Generate one slide image at a time based on the slide type requested.'''

    def generate_slide_prompts(self) -> List[Dict[str, str]]:
        """Generate individual prompts for each slide."""
        prompts = []

        # Slide 1: Title
        prompts.append({
            "slide_number": 1,
            "slide_type": "title",
            "prompt": f'''Create a professional title slide for "{self.context.company_name}"

Style: {self.context.visual_style}, {self.context.color_scheme} color scheme
Include:
- Large, bold company name: "{self.context.company_name}"
- Tagline area for: "AI-Powered Lead Generation for Local Businesses"
- Subtle background graphic suggesting growth/technology
- Clean, modern typography

The slide should feel premium and trustworthy, targeting {self.context.target_audience}.'''
        })

        # Slide 2: Problem
        prompts.append({
            "slide_number": 2,
            "slide_type": "problem",
            "prompt": f'''Create a "Problem" slide showing the pain points of local businesses

Headline: "The Problem" or "Why Local Businesses Struggle"
Visual elements:
- Show frustrated business owner or declining graph
- Statistics visualization: "78% of local searches lead to offline purchases, but most businesses are invisible"
- Pain point: "{self.context.main_problem}"
- Use {self.context.color_scheme} accents with darker tones to convey the problem
- Style: {self.context.visual_style}

Make it emotional but professional.'''
        })

        # Slide 3: Solution
        prompts.append({
            "slide_number": 3,
            "slide_type": "solution",
            "prompt": f'''Create a "Solution" slide introducing {self.context.company_name}

Headline: "The Solution" or "Enter {self.context.company_name}"
Visual elements:
- Bright, optimistic design (contrast from problem slide)
- Simple before/after or transformation visual
- Key benefit: "{self.context.unique_value}"
- 3 solution icons representing: {", ".join(self.context.key_solutions[:3]) if self.context.key_solutions else "AI, Automation, Results"}
- {self.context.color_scheme} primary color, {self.context.visual_style} style

Convey hope and capability.'''
        })

        # Slide 4: How It Works
        prompts.append({
            "slide_number": 4,
            "slide_type": "how_it_works",
            "prompt": f'''Create a "How It Works" slide showing the Rise Local pipeline

Headline: "How It Works" or "Your Growth Engine"
Visual: A horizontal pipeline/funnel diagram with 5 stages:
1. Discover (find leads) - magnifying glass icon
2. Enrich (gather intel) - data/chart icon
3. Score (qualify) - checkmark/rating icon
4. Personalize (AI emails) - AI/robot icon
5. Deliver (multi-channel) - send/rocket icon

Style: {self.context.visual_style}, {self.context.color_scheme} gradient
Clean infographic style, numbered steps, icons for each stage.'''
        })

        # Slide 5: Features
        feature_list = self.context.key_solutions[:6] if self.context.key_solutions else [
            "AI Lead Scoring", "Personalized Outreach", "Multi-Channel Delivery"
        ]
        prompts.append({
            "slide_number": 5,
            "slide_type": "features",
            "prompt": f'''Create a "Features" slide showcasing key capabilities

Headline: "What You Get" or "Key Features"
Visual: Grid layout with icons and short labels for each feature:
{chr(10).join(f"- {feat}" for feat in feature_list)}

Style: {self.context.visual_style}
- Each feature gets an icon + 2-3 word label
- {self.context.color_scheme} icons on light background
- Clean grid, 2x3 or 3x2 layout
- Consistent icon style throughout'''
        })

        # Slide 6: Results
        stats = self.context.results_stats or {
            "response_rate": "23%",
            "qualified_leads": "50+/mo",
            "time_saved": "40 hrs/week"
        }
        prompts.append({
            "slide_number": 6,
            "slide_type": "results",
            "prompt": f'''Create a "Results" slide with impressive statistics

Headline: "Real Results" or "The Numbers Don't Lie"
Visual: Large statistics display with:
{chr(10).join(f"- {k.replace('_', ' ').title()}: {v}" for k, v in stats.items())}

Style: {self.context.visual_style}
- Big, bold numbers
- Supporting context below each stat
- {self.context.color_scheme} accent color for numbers
- Optional: subtle upward graph in background
- Clean, data-visualization style'''
        })

        # Slide 7: Pricing
        packages = self.context.packages or [
            {"name": "Starter", "price": "$497/mo", "leads": "25 leads"},
            {"name": "Growth", "price": "$997/mo", "leads": "50 leads"},
            {"name": "Scale", "price": "$1,997/mo", "leads": "100+ leads"}
        ]
        prompts.append({
            "slide_number": 7,
            "slide_type": "pricing",
            "prompt": f'''Create a "Pricing" slide with tier comparison

Headline: "Choose Your Plan" or "Simple Pricing"
Visual: 3-column pricing table
{chr(10).join(f"- {pkg['name']}: {pkg['price']} - {pkg['leads']}" for pkg in packages)}

Style: {self.context.visual_style}
- Middle tier (Growth) highlighted as "Most Popular"
- {self.context.color_scheme} for highlighted tier
- Checkmarks for included features
- Clean comparison layout
- Clear visual hierarchy'''
        })

        # Slide 8: CTA
        prompts.append({
            "slide_number": 8,
            "slide_type": "cta",
            "prompt": f'''Create a "Call to Action" closing slide

Headline: "Ready to Grow?" or "Let's Get Started"
Main CTA: "{self.context.cta_action}"
Visual elements:
- Large, prominent CTA button
- Contact info area (email, phone, website)
- {self.context.company_name} logo
- Subtle urgency element ("Limited spots available" or "Start this week")

Style: {self.context.visual_style}, {self.context.color_scheme}
- Energetic, action-oriented design
- Clear next step
- Professional but inviting'''
        })

        return prompts

    def export_all(self, filename: str = None) -> str:
        """Export system prompt and all slide prompts to file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"deck_prompts_{timestamp}.json"

        output = {
            "generated_at": datetime.now().isoformat(),
            "context": {
                "company": self.context.company_name,
                "audience": self.context.target_audience,
                "style": self.context.visual_style,
                "colors": self.context.color_scheme
            },
            "system_prompt": self.generate_system_prompt(),
            "slide_prompts": self.generate_slide_prompts()
        }

        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)

        return filename

    def print_prompts(self):
        """Print all prompts to console."""
        print("\n" + "=" * 60)
        print("SYSTEM PROMPT (for Google AI Studio)")
        print("=" * 60)
        print(self.generate_system_prompt())

        print("\n" + "=" * 60)
        print("SLIDE PROMPTS (for Nano Banana)")
        print("=" * 60)

        for slide in self.generate_slide_prompts():
            print(f"\n--- Slide {slide['slide_number']}: {slide['slide_type'].upper()} ---")
            print(slide['prompt'])


def main():
    """Main entry point."""
    import sys

    # Run question operation
    qop = QuestionOperation()

    if "--quick" in sys.argv:
        # Use defaults for quick testing
        context = DeckContext(
            target_audience="Local service business owners",
            main_problem="They're invisible online - losing customers to competitors",
            key_solutions=["AI-powered lead qualification", "Automated outreach", "Performance analytics"],
            unique_value="10-point pain scoring system finds leads others miss",
            results_stats={"response_rate": "23%", "qualified_leads": "50+/mo", "time_saved": "40 hrs"},
            packages=[
                {"name": "Starter", "price": "$497/mo", "leads": "25 leads"},
                {"name": "Growth", "price": "$997/mo", "leads": "50 leads"},
                {"name": "Scale", "price": "$1,997/mo", "leads": "100+ leads"}
            ],
            cta_action="Book a demo call",
            visual_style="Modern minimal",
            color_scheme="Blue"
        )
    else:
        context = qop.run_interactive()

    # Generate prompts
    generator = NanoBananaPromptGenerator(context)

    if "--export" in sys.argv:
        filename = generator.export_all()
        print(f"\nPrompts exported to: {filename}")
    else:
        generator.print_prompts()

    print("\n" + "=" * 60)
    print("NEXT STEPS:")
    print("=" * 60)
    print("1. Copy the SYSTEM PROMPT into Google AI Studio")
    print("2. For each slide, paste the SLIDE PROMPT into Gemini/Nano Banana")
    print("3. Use 'Beautify this slide' in Google Slides for final polish")
    print("4. Add your actual text/data to the generated visuals")


if __name__ == "__main__":
    main()
