"""
Industrial, professional manufacturing ERP styling for FactoryFlow.
Design principles:
- Deep Slate Navy (#141e28)
- Muted Cool Grey (#eef1f4)
- Warm Off-White Surfaces (#f8f9fa)
- Deep Spruce Teal Accents (#0b645b)
- System typography (Segoe UI, -apple-system, Arial)
- Crisp 2-3px radius borders, zero drop shadows, zero emojis
"""


def render_header(title: str, subtitle: str = "") -> str:
    """Returns HTML for formal enterprise page title banner."""
    return f"""
    <div style="border-bottom: 1px solid #d1d5db; padding-bottom: 10px; margin-bottom: 18px;">
        <h2 style="color: #111827; margin: 0 0 4px 0; font-size: 22px; font-weight: 700;">{title}</h2>
        {f'<div style="color: #4b5563; font-size: 13px;">{subtitle}</div>' if subtitle else ''}
    </div>
    """


def render_metric(title: str, value: str, subtext: str = "") -> str:
    """Returns HTML for a flat metric panel."""
    return f"""
    <div class="ff-metric-panel">
        <div class="ff-metric-label">{title}</div>
        <div class="ff-metric-num">{value}</div>
        {f'<div class="ff-metric-note">{subtext}</div>' if subtext else ''}
    </div>
    """
