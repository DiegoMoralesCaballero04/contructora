"""Temporary script to patch .po files with missing translations."""
import re

TRANSLATIONS = {
    "Les contrasenyes no coincideixen.": ("Las contraseñas no coinciden.", "Passwords do not match."),
    "La contrasenya ha de tenir mínim 8 caràcters.": ("La contraseña debe tener mínimo 8 caracteres.", "Password must be at least 8 characters."),
    "Perfil actualitzat.": ("Perfil actualizado.", "Profile updated."),
    "Contrasenya actualitzada correctament.": ("Contraseña actualizada correctamente.", "Password updated successfully."),
    "Mi perfil": ("Mi perfil", "My profile"),
    "Datos personales": ("Datos personales", "Personal data"),
    "Cambiar contraseña": ("Cambiar contraseña", "Change password"),
    "Nueva contraseña": ("Nueva contraseña", "New password"),
    "Confirmar contraseña": ("Confirmar contraseña", "Confirm password"),
    "Dejar en blanco para no cambiar": ("Dejar en blanco para no cambiar", "Leave blank to keep current"),
    "Guardar cambios": ("Guardar cambios", "Save changes"),
    "Nom / Raó social": ("Nombre / Razón social", "Name / Company name"),
    "Adreça": ("Dirección", "Address"),
    "Client": ("Cliente", "Client"),
    "Clients": ("Clientes", "Clients"),
    "Esborrany": ("Borrador", "Draft"),
    "Confirmat": ("Confirmado", "Confirmed"),
    "En curs": ("En curso", "In progress"),
    "Completat": ("Completado", "Completed"),
    "Cancel·lat": ("Cancelado", "Cancelled"),
    "Número": ("Número", "Number"),
    "Data d'entrega": ("Fecha de entrega", "Delivery date"),
    "Ref. client": ("Ref. cliente", "Client ref."),
    "Pedido": ("Pedido", "Order"),
    "Pedidos": ("Pedidos", "Orders"),
    "Emès": ("Emitido", "Issued"),
    "Facturat": ("Facturado", "Invoiced"),
    "Albarà": ("Albarán", "Delivery note"),
    "Albarans": ("Albaranes", "Delivery notes"),
    "Emesa": ("Emitida", "Issued"),
    "Cobrada": ("Cobrada", "Paid"),
    "Vençuda": ("Vencida", "Overdue"),
    "Ordi\\u00e0ria": ("Ordinaria", "Standard"),
    "Rectificativa": ("Rectificativa", "Credit note"),
    "Proforma": ("Proforma", "Proforma"),
    "Sèrie": ("Serie", "Series"),
    "Número complet": ("Número completo", "Full number"),
    "Document adjunt (PDF/imatge)": ("Documento adjunto (PDF/imagen)", "Attached document (PDF/image)"),
    "Dades extretes per IA": ("Datos extraídos por IA", "AI-extracted data"),
    "Factura rectificada": ("Factura rectificada", "Rectified invoice"),
    "Factura": ("Factura", "Invoice"),
    "Factures": ("Facturas", "Invoices"),
    "Nova factura": ("Nueva factura", "New invoice"),
    "Data emissió": ("Fecha de emisión", "Issue date"),
    "Data venciment": ("Fecha de vencimiento", "Due date"),
    "Base imposable": ("Base imponible", "Tax base"),
    "Retenció IRPF": ("Retención IRPF", "IRPF withholding"),
    "Enviar a VerifactuRE": ("Enviar a VerifactuRE", "Submit to VerifactuRE"),
    "Enviat": ("Enviado", "Sent"),
    "Document adjunt": ("Documento adjunto", "Attached document"),
    "Resum econòmic": ("Resumen económico", "Economic summary"),
    "Canviar estat": ("Cambiar estado", "Change status"),
    "Actualitzar": ("Actualizar", "Update"),
    "Descripció": ("Descripción", "Description"),
    "Quantitat": ("Cantidad", "Quantity"),
    "Preu unit.": ("Precio unit.", "Unit price"),
    "Subtotal": ("Subtotal", "Subtotal"),
    "Cap factura trobada.": ("Ninguna factura encontrada.", "No invoices found."),
    "Cap albarà trobat.": ("Ningún albarán encontrado.", "No delivery notes found."),
    "Cap pedido trobat.": ("Ningún pedido encontrado.", "No orders found."),
    "Cap client trobat.": ("Ningún cliente encontrado.", "No clients found."),
    "Tots els estats": ("Todos los estados", "All statuses"),
    "Netejar": ("Limpiar", "Clear"),
    "Selecciona client": ("Selecciona cliente", "Select client"),
    "Crear nou client": ("Crear nuevo cliente", "Create new client"),
    "Crear factura": ("Crear factura", "Create invoice"),
    "Nou client": ("Nuevo cliente", "New client"),
    "Guardar client": ("Guardar cliente", "Save client"),
    "Codi postal": ("Código postal", "Postal code"),
    "Població": ("Población", "City"),
    "Província": ("Provincia", "Province"),
    "País": ("País", "Country"),
    "Nom del rol": ("Nombre del rol", "Role name"),
    "Rols personalitzats": ("Roles personalizados", "Custom roles"),
    "Nou rol": ("Nuevo rol", "New role"),
    "Editar rol": ("Editar rol", "Edit role"),
    "Guardar rol": ("Guardar rol", "Save role"),
    "Cancel·lar": ("Cancelar", "Cancel"),
    "Veure licitaciones": ("Ver licitaciones", "View tenders"),
    "Editar licitaciones": ("Editar licitaciones", "Edit tenders"),
    "Veure marketing / prospects": ("Ver marketing / prospects", "View marketing / prospects"),
    "Editar marketing / prospects": ("Editar marketing / prospects", "Edit marketing / prospects"),
    "Veure ERP (factures, albarans, pedidos)": ("Ver ERP (facturas, albaranes, pedidos)", "View ERP (invoices, delivery notes, orders)"),
    "Editar ERP": ("Editar ERP", "Edit ERP"),
    "Veure RRHH / fitxatges": ("Ver RRHH / fichajes", "View HR / timesheets"),
    "Veure documents": ("Ver documentos", "View documents"),
    "Pujar documents": ("Subir documentos", "Upload documents"),
    "Usar IA / RAG": ("Usar IA / RAG", "Use AI / RAG"),
    "Gestionar usuaris": ("Gestionar usuarios", "Manage users"),
    "Gestionar rols personalitzats": ("Gestionar roles personalizados", "Manage custom roles"),
    "Veure panell d'administració": ("Ver panel de administración", "View admin panel"),
    "Rols i permisos": ("Roles y permisos", "Roles & permissions"),
    "Pujar document": ("Subir documento", "Upload document"),
    "Extraure dades amb IA": ("Extraer datos con IA", "Extract data with AI"),
    "Document pujat i dades extretes per IA.": ("Documento subido y datos extraídos por IA.", "Document uploaded and data extracted by AI."),
    "Document pujat. La IA no ha pogut extreure dades estructurades.": ("Documento subido. La IA no pudo extraer datos estructurados.", "Document uploaded. AI could not extract structured data."),
    "Format no admès. Puja un PDF o imatge.": ("Formato no admitido. Sube un PDF o imagen.", "Format not supported. Upload a PDF or image."),
    "Selecciona un fitxer PDF o imatge.": ("Selecciona un archivo PDF o imagen.", "Select a PDF or image file."),
    "Analitzar document": ("Analizar documento", "Analyze document"),
    "Analitzar amb IA": ("Analizar con IA", "Analyze with AI"),
    "Tipus de document": ("Tipo de documento", "Document type"),
    "Dades extretes": ("Datos extraídos", "Extracted data"),
    "Revisar i crear": ("Revisar y crear", "Review and create"),
    "Tancar sessió": ("Cerrar sesión", "Sign out"),
    "Mi perfil": ("Mi perfil", "My profile"),
    "Pendent d'enviar a l'AEAT": ("Pendiente de enviar a la AEAT", "Pending submission to AEAT"),
    "Quantes licitacions tenim en total i quantes són noves?": ("¿Cuántas licitaciones tenemos en total y cuántas son nuevas?", "How many tenders do we have in total and how many are new?"),
    "Quants prospects tenim i quants han passat a ser clients?": ("¿Cuántos prospects tenemos y cuántos han pasado a ser clientes?", "How many prospects do we have and how many became clients?"),
    "Quin és l'import total de les factures pendents de cobrament?": ("¿Cuál es el importe total de las facturas pendientes de cobro?", "What is the total amount of pending invoices?"),
    "Quantes ofertes hem guanyat?": ("¿Cuántas ofertas hemos ganado?", "How many offers have we won?"),
    "Llista els documents ISO actius.": ("Lista los documentos ISO activos.", "List active ISO documents."),
    "Defineix rols amb permisos granulars per assignar als usuaris.": ("Define roles con permisos granulares para asignar a los usuarios.", "Define roles with granular permissions to assign to users."),
    "No hi ha rols personalitzats. Crea el primer per personalitzar els permisos dels usuaris.": (
        "No hay roles personalizados. Crea el primero para personalizar los permisos de los usuarios.",
        "No custom roles. Create the first one to customize user permissions."
    ),
    "Reial Decret 1007/2023. Opcional fins al termini legal obligatori.": (
        "Real Decreto 1007/2023. Opcional hasta el plazo legal obligatorio.",
        "Royal Decree 1007/2023. Optional until the mandatory legal deadline."
    ),
    "Si s'especifica, els permisos es prenen del rol personalitzat.": (
        "Si se especifica, los permisos provienen del rol personalizado.",
        "If specified, permissions come from the custom role."
    ),
    "Si s'assigna, els permisos vénen del rol personalitzat.": (
        "Si se asigna, los permisos vienen del rol personalizado.",
        "If assigned, permissions come from the custom role."
    ),
    "Gestionar roles": ("Gestionar roles", "Manage roles"),
    "Rol base": ("Rol base", "Base role"),
    "S'utilitza si no hi ha rol personalitzat.": ("Se usa si no hay rol personalizado.", "Used if no custom role is set."),
    "Cap (usar rol base)": ("Ninguno (usar rol base)", "None (use base role)"),
    "Gestionar rols": ("Gestionar roles", "Manage roles"),
    "Nou usuari": ("Nuevo usuario", "New user"),
    "Hola! Soc el teu assistent IA. Puc respondre preguntes sobre documents indexats i sobre les dades en temps real de l'aplicació: licitacions, prospects, factures, ofertes i més. Prova a preguntar-me qualsevol cosa.": (
        "Hola! Soy tu asistente IA. Puedo responder preguntas sobre documentos indexados y sobre los datos en tiempo real de la aplicación: licitaciones, prospects, facturas, ofertas y más. Prueba a preguntarme cualquier cosa.",
        "Hello! I'm your AI assistant. I can answer questions about indexed documents and real-time application data: tenders, prospects, invoices, offers and more. Try asking me anything."
    ),
    "Total pendent de cobrament: %(total)s €": ("Total pendiente de cobro: %(total)s €", "Total pending collection: %(total)s €"),
    "Tornar": ("Volver", "Back"),
    "Guardar": ("Guardar", "Save"),
    "Total facturat: %(total)s €": ("Total facturado: %(total)s €", "Total invoiced: %(total)s €"),
    "Estat actualitzat.": ("Estado actualizado.", "Status updated."),
    "Client creat correctament.": ("Cliente creado correctamente.", "Client created successfully."),
    "Factura creada. Ara podeu afegir les l'ínies.": ("Factura creada. Ahora puedes añadir las líneas.", "Invoice created. You can now add lines."),
    "Factura creada. Ara podeu afegir les línies.": ("Factura creada. Ahora puedes añadir las líneas.", "Invoice created. You can now add lines."),
    "El nom és obligatori.": ("El nombre es obligatorio.", "Name is required."),
    "El nom del rol és obligatori.": ("El nombre del rol es obligatorio.", "Role name is required."),
    "Rol creat correctament.": ("Rol creado correctamente.", "Role created successfully."),
    "Rol actualitzat.": ("Rol actualizado.", "Role updated."),
    "Introdueix una ubicació per cercar empreses properes.": (
        "Introduce una ubicación para buscar empresas cercanas.",
        "Enter a location to search for nearby businesses."
    ),
}


def patch_po(filepath, lang_idx):
    with open(filepath, encoding='utf-8') as f:
        content = f.read()

    added = 0
    for msgid, translations in TRANSLATIONS.items():
        trans = translations[lang_idx]
        escaped_id = msgid.replace('\\', '\\\\').replace('"', '\\"')
        escaped_trans = trans.replace('\\', '\\\\').replace('"', '\\"')
        old = f'msgid "{escaped_id}"\nmsgstr ""'
        new = f'msgid "{escaped_id}"\nmsgstr "{escaped_trans}"'
        if old in content:
            content = content.replace(old, new)
            added += 1

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return added


import os
base = os.path.join(os.path.dirname(__file__), 'locale')
r_es = patch_po(os.path.join(base, 'es', 'LC_MESSAGES', 'django.po'), 0)
r_en = patch_po(os.path.join(base, 'en', 'LC_MESSAGES', 'django.po'), 1)
print(f'ES: {r_es} strings added | EN: {r_en} strings added')
