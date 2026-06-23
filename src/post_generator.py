from datetime import datetime
from .database import get_today_numbers
from .rag import get_description_for_number

PLANET_NAMES = [
    "Солнце", "Земля", "Луна", "Меркурий", "Венера", "Марс",
    "Юпитер", "Сатурн", "Уран", "Нептун", "Плутон",
    "Северный узел", "Южный узел"
]

def generate_post_content(date_str: str = None) -> str:
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    pairs = get_today_numbers(date_str)
    blocks = []
    
    for idx, (gate, line) in enumerate(pairs):
        planet = PLANET_NAMES[idx] if idx < len(PLANET_NAMES) else f"Планета {idx+1}"
        gate_line = f"{gate}.{line}"
        desc, _ = get_description_for_number(gate, line)
        
        block = f"""
        <div class="transit-block" data-gate-line="{gate_line}">
            <h3>{planet} в {gate_line}</h3>
            <p class="essence"><strong>Суть:</strong> {desc}</p>
            <a href="/chat?gate={gate_line}" class="discuss-link">Обсудить эту энергию →</a>
        </div>
        """
        blocks.append(block)
    
    html = f"""
    <div class="post-container">
        <h2>Транзиты на {date_str}</h2>
        <div class="transits-list">
            {''.join(blocks)}
        </div>
    </div>
    """
    return html