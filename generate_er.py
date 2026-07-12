# ruff: noqa: F403
import sys
import os

sys.path.insert(0, "/home/ramon/projects/everacy/yummydoors_backend")

# Import all models to register them with SQLAlchemy Base
from app.modules.reservations.models import *
from app.modules.restaurants.models import *
from app.modules.rider_applications.models import *
from app.modules.carts.models import *
from app.modules.customers.models import *
from app.modules.notifications.models import *
from app.modules.merchandising.models import *
from app.modules.messages.models import *
from app.modules.workspaces.models import *
from app.modules.catalog.models import *
from app.modules.auth.models import *
from app.modules.integrations.pos.models import *
from app.modules.favorites.models import *
from app.modules.orders.models import *

from app.db.base import Base

def generate_mermaid_er(metadata):
    mermaid = "erDiagram\n"
    
    for table_name, table in metadata.tables.items():
        # Sanitize table names if needed, usually fine
        mermaid += f"    {table_name} {{\n"
        for column in table.columns:
            col_type = str(column.type).split('(')[0]
            col_type = col_type.replace(' ', '_').replace('[]', '_ARRAY')
            pk = "PK" if column.primary_key else ""
            fk = "FK" if column.foreign_keys else ""
            key = f"{pk},{fk}".strip(',')
            mermaid += f"        {col_type} {column.name} {key}\n"
        mermaid += "    }\n"
        
        # Add relationships based on foreign keys
        for column in table.columns:
            for fk in column.foreign_keys:
                target_table = fk.column.table.name
                mermaid += f"    {target_table} ||--o{{ {table_name} : \"{column.name}\"\n"
                
    return mermaid

mermaid_script = generate_mermaid_er(Base.metadata)

with open('er_diagram.mermaid', 'w') as f:
    f.write(mermaid_script)
    
print("Successfully generated er_diagram.mermaid")

# Now generate SVG from mermaid using mermaid.ink
import base64
import urllib.request
encoded_code = base64.urlsafe_b64encode(mermaid_script.encode('utf-8')).decode('utf-8').rstrip('=')
url = f'https://mermaid.ink/svg/{encoded_code}?bgColor=!white'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response, open('/mnt/c/Users/ramon/Desktop/YummyDoors_Database_ER_Diagram.svg', 'wb') as out_file:
        out_file.write(response.read())
    print("Successfully downloaded SVG to Desktop!")
except Exception as e:
    print("Failed to download SVG:", e)
