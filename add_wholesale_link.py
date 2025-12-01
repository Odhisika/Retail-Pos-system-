#!/usr/bin/env python3
"""Add Wholesale link to base.html navigation"""

# Read the file
with open(r'c:\Users\francis\Desktop\django-pos\templates\base.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Define the wholesale link HTML
wholesale_link = """
                <a href="{% url 'wholesale:dashboard' %}"
                    class="nav-link flex items-center px-4 py-3 text-gray-300 hover:bg-dark-700 hover:text-white transition-colors {% if 'wholesale' in request.path %}bg-dark-700 text-white border-l-4 border-primary-500{% endif %}">
                    <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4">
                        </path>
                    </svg>
                    <span class="ml-3 nav-text">Wholesale</span>
                </a>
"""

# Find the position after the POS link closing tag (line 155: </a>)
# and before the {% endif %} (line 156)
# Insert the wholesale link there

# Split into lines
lines = content.split('\n')

# Find line 155 (</a> after POS link) - it's 0-indexed so line 154
# Insert after line 155, before line 156 ({% endif %})
insert_position = 155  # After line 155 (0-indexed: 154)

# Insert the wholesale link
lines.insert(insert_position, wholesale_link)

# Join back
new_content = '\n'.join(lines)

# Write back
with open(r'c:\Users\francis\Desktop\django-pos\templates\base.html', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ Wholesale link added successfully!")
