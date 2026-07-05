"""
╔══════════════════════════════════════════════════════════════╗
║         SERENOVA — Bot de Commande v3 Final                  ║
╚══════════════════════════════════════════════════════════════╝
"""
import logging, random, string, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters, ContextTypes,
)

# ═══════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════
TOKEN        = "8828533872:AAHhUVqA5e0gncPGESeZc2YkHjyrLq-iLXY"
ADMIN_ID     = 8983097960
FAQ_LINK     = "https://t.me/serenovacommunity/31"
SUPPORT      = "https://t.me/serenovalabsupport"
PAYMENT_LINK = ""
FRAIS_MAIN   = 0
FRAIS_FR     = 5
FRAIS_EU     = 15
REMINDER_SEC = 1800  # 30 minutes

# ═══════════════════════════════════════════
# CATALOGUE
# ═══════════════════════════════════════════
PRODUITS = {
    "reta":   {"nom": "Retatrutide · 10mg",  "prix": 90},
    "tb500":  {"nom": "TB-500 · 5mg",        "prix": 90},
    "bpc157": {"nom": "BPC-157 · 5mg",       "prix": 70},
    "ghk":    {"nom": "GHK-Cu · 50mg",       "prix": 70},
}

# ═══════════════════════════════════════════
# ÉTATS
# ═══════════════════════════════════════════
(
    HOME, CATALOGUE_STATE, QUANTITY_STATE, CUSTOM_QTY,
    SERINGUE_STATE, CART_STATE, DELIVERY_STATE, PAYMENT_METHOD_MAIN,
    INFO_FNAME, INFO_LNAME, INFO_ADDRESS, INFO_PHONE,
    RECAP_STATE, PAYMENT_STATE,
) = range(14)

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# ═══════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════
def gen_ref():
    return "SRN-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

def sep():  return "━━━━━━━━━━━━━━━━━━━━━"
def kb(b):  return InlineKeyboardMarkup(b)

def cart_lines(cart):
    return "".join(f"💉 {i['nom']} x{i['qte']} → {i['prix']*i['qte']}€\n" for i in cart)

def cart_total(cart, frais):
    sub = sum(i["prix"] * i["qte"] for i in cart)
    return sub, sub + frais

def back_btn(data="back"):
    return InlineKeyboardButton("◀️  Retour", callback_data=data)

def help_btn():
    return InlineKeyboardButton("🆘  Besoin d'aide ?", url=SUPPORT)


# ═══════════════════════════════════════════
# RELANCE PANIER (job planifié)
# ═══════════════════════════════════════════
async def cart_reminder(context: ContextTypes.DEFAULT_TYPE):
    job  = context.job
    data = job.data
    cart = data.get("cart", [])
    if not cart or data.get("completed"):
        return
    frais  = data.get("frais", FRAIS_FR)
    sub, total = cart_total(cart, frais)
    msg = (
        f"{sep()}\n"
        "🛒 *Votre panier est prêt*\n\n"
        "Procédez au paiement de votre commande\n\n"
        + cart_lines(cart)
        + f"\n💰 *Total : {total}€*\n\n"
        f"{sep()}\n"
    )
    buttons = [[InlineKeyboardButton("🚀  Continuer ma commande", callback_data="resume_cart")]]
    try:
        await context.bot.send_message(
            chat_id=data["chat_id"],
            text=msg,
            reply_markup=kb(buttons),
            parse_mode="Markdown",
        )
    except Exception as e:
        logging.error(f"Reminder failed: {e}")


def schedule_reminder(ctx, update, cart):
    if not ctx.job_queue:
        return
    try:
        jobs = ctx.job_queue.get_jobs_by_name(f"reminder_{update.effective_user.id}")
        for j in jobs:
            j.schedule_removal()
        ctx.job_queue.run_once(
            cart_reminder,
            REMINDER_SEC,
            data={
                "cart":    cart,
                "frais":   ctx.user_data.get("frais", FRAIS_FR),
                "chat_id": update.effective_chat.id,
                "completed": False,
            },
            name=f"reminder_{update.effective_user.id}",
        )
    except Exception as e:
        logging.warning(f"Reminder non disponible: {e}")


def cancel_reminder(ctx, user_id):
    if not ctx.job_queue:
        return
    try:
        jobs = ctx.job_queue.get_jobs_by_name(f"reminder_{user_id}")
        for j in jobs:
            j.schedule_removal()
    except Exception:
        pass


# ═══════════════════════════════════════════
# PAGE 1 — ACCUEIL
# ═══════════════════════════════════════════
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    prenom = update.effective_user.first_name or "vous"
    msg = (
        f"👋 Bonjour *{prenom}* !\n\n"
        "Bienvenue sur votre bot de commande *Serenova*.\n"
        f"{sep()}\n\n"
        "🧬 *Nos peptides disponibles :*\n"
        "• Retatrutide (RETA)\n"
        "• TB-500\n"
        "• BPC-157\n"
        "• GHK-Cu\n\n"
        "💳 *Paiements acceptés :*\n"
        "• PayPal · Carte bancaire\n"
        "• Apple Pay · Google Pay\n"
        "• Revolut · Crypto\n\n"
        "📦 *Service de livraison* ou remise en main propre 🤝\n\n"
        f"{sep()}\n"
        "👇 Cliquez sur *Commander* pour effectuer une commande"
    )
    buttons = [
        [InlineKeyboardButton("🛒  Commander", callback_data="go_catalogue")],
        [InlineKeyboardButton("❓  FAQ",        url=FAQ_LINK)],
    ]
    if update.message:
        await update.message.reply_text(msg, reply_markup=kb(buttons), parse_mode="Markdown")
    else:
        try:
            await update.callback_query.edit_message_text(msg, reply_markup=kb(buttons), parse_mode="Markdown")
        except Exception:
            await update.effective_message.reply_text(msg, reply_markup=kb(buttons), parse_mode="Markdown")
    return HOME


# ═══════════════════════════════════════════
# PAGE 2 — CATALOGUE
# ═══════════════════════════════════════════
async def show_catalogue(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    msg = (
        f"{sep()}\n"
        "🧬 *CATALOGUE SERENOVA*\n\n"
        "👇 Sélectionnez votre peptide :\n"
    )
    buttons = [
        [InlineKeyboardButton(f"💉  {p['nom']} — {p['prix']}€", callback_data=f"prod_{pid}")]
        for pid, p in PRODUITS.items()
    ]
    buttons.append([back_btn("go_home"), InlineKeyboardButton("🏠  Accueil", callback_data="go_home")])
    edit = bool(update.callback_query)
    if edit:
        try:
            await update.callback_query.edit_message_text(msg, reply_markup=kb(buttons), parse_mode="Markdown")
            return CATALOGUE_STATE
        except Exception:
            pass
    await update.effective_message.reply_text(msg, reply_markup=kb(buttons), parse_mode="Markdown")
    return CATALOGUE_STATE


# ═══════════════════════════════════════════
# PAGE 3 — ÉTAPE 1/5 PRODUIT
# ═══════════════════════════════════════════
async def show_product(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    pid  = q.data.replace("prod_", "")
    prod = PRODUITS.get(pid)
    if not prod:
        return CATALOGUE_STATE
    ctx.user_data["prod_id"]   = pid
    ctx.user_data["prod_nom"]  = prod["nom"]
    ctx.user_data["prod_prix"] = prod["prix"]
    msg = (
        f"{sep()}\n"
        "🧭 *Étape 1/5 — Produit*\n\n"
        f"💉 *{prod['nom']}*\n"
        f"💰 Prix : *{prod['prix']}€ la fiole*\n\n"
        "✅ *Inclus dans chaque commande :*\n"
        "• 2 seringues à insuline\n"
        "• 1 fiole d'eau bactériostatique\n"
        "• 5 tampons d'alcool\n\n"
        "Choisissez votre quantité :\n"
    )
    buttons = [
        [InlineKeyboardButton("1 fiole",  callback_data="qty_1"),
         InlineKeyboardButton("2 fioles", callback_data="qty_2")],
        [InlineKeyboardButton("✏️  Autre quantité", callback_data="qty_custom")],
        [back_btn("go_catalogue")],
    ]
    await q.edit_message_text(msg, reply_markup=kb(buttons), parse_mode="Markdown")
    return QUANTITY_STATE


async def set_quantity(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "qty_custom":
        await q.edit_message_text(
            f"{sep()}\n✏️ Entrez votre quantité (ex: 3) :\n\n",
            reply_markup=kb([[back_btn("go_catalogue")]]),
            parse_mode="Markdown",
        )
        return CUSTOM_QTY
    return await add_to_cart(update, ctx, int(q.data.replace("qty_", "")))


async def custom_quantity(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        qte = int(update.message.text.strip())
        if qte < 1: raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Entrez un nombre valide (ex: 3) :")
        return CUSTOM_QTY
    return await add_to_cart(update, ctx, qte, from_msg=True)


async def add_to_cart(update, ctx, qte, from_msg=False):
    cart = ctx.user_data.setdefault("cart", [])
    nom, prix = ctx.user_data["prod_nom"], ctx.user_data["prod_prix"]
    for item in cart:
        if item["nom"] == nom:
            item["qte"] += qte
            break
    else:
        cart.append({"nom": nom, "prix": prix, "qte": qte})
    schedule_reminder(ctx, update, cart)
    return await show_seringue(update, ctx, from_msg=from_msg)



# ═══════════════════════════════════════════
# PACK SERINGUE EN OPTION
# ═══════════════════════════════════════════
async def show_seringue(update, ctx, from_msg=False):
    # ── OFFRE D'ÉTÉ active jusqu'au 1er septembre ───────────
    msg = (
        f"{sep()}\n"
        "🌞 *OFFRE D'ÉTÉ*\n\n"
        "Du 1er au 31 juillet, le pack seringue est *offert* !\n\n"
        "💉 *Pack seringue inclus :*\n"
        "• 10 seringues à insuline 1 ml\n"
        "• 10 tampons d'alcool\n\n"
        "Voulez-vous en bénéficier ?\n"
    )
    buttons = [
        [InlineKeyboardButton("✅  Oui, j'en bénéficie !", callback_data="seringue_yes")],
        [InlineKeyboardButton("❌  Non merci, continuer",  callback_data="seringue_no")],
    ]
    # ── À RÉACTIVER APRÈS LE 1ER SEPTEMBRE ──────────────────
    # msg = (
    #     f"{sep()}\n"
    #     "💉 *PACK SERINGUE EN OPTION*\n\n"
    #     "Nécessaire pour les injections.\n\n"
    #     "Ajoutez le pack seringue pour *10€* :\n"
    #     "• 10 seringues à insuline 1 ml\n"
    #     "• 10 tampons d'alcool\n"
    # )
    # buttons = [
    #     [InlineKeyboardButton("✅  Oui, ajouter (+10€)",  callback_data="seringue_yes")],
    #     [InlineKeyboardButton("❌  Non merci, continuer", callback_data="seringue_no")],
    # ]
    # ────────────────────────────────────────────────────────
    if from_msg:
        await update.message.reply_text(msg, reply_markup=kb(buttons), parse_mode="Markdown")
    else:
        try:
            await update.callback_query.edit_message_text(msg, reply_markup=kb(buttons), parse_mode="Markdown")
        except Exception:
            await update.effective_message.reply_text(msg, reply_markup=kb(buttons), parse_mode="Markdown")
    return SERINGUE_STATE


async def seringue_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "seringue_yes":
        cart = ctx.user_data.setdefault("cart", [])
        # OFFRE D'ÉTÉ : pack offert (prix 0€)
        for item in cart:
            if item["nom"] == "Pack Seringue (Offert)":
                break
        else:
            cart.append({"nom": "Pack Seringue (Offert)", "prix": 0, "qte": 1})
        # ── À RÉACTIVER APRÈS LE 1ER SEPTEMBRE ──
        # for item in cart:
        #     if item["nom"] == "Pack Seringue":
        #         item["qte"] += 1
        #         break
        # else:
        #     cart.append({"nom": "Pack Seringue", "prix": 10, "qte": 1})
        # ────────────────────────────────────────
    return await show_cart(update, ctx)


# ═══════════════════════════════════════════
# PAGE 4 — ÉTAPE 2/5 PANIER
# ═══════════════════════════════════════════
async def show_cart(update, ctx, from_msg=False):
    cart  = ctx.user_data.get("cart", [])
    frais = ctx.user_data.get("frais", FRAIS_FR)
    sub, _ = cart_total(cart, frais)
    msg = (
        f"{sep()}\n"
        "🧭 *Étape 2/5 — Panier*\n\n"
        "🛒 *VOTRE PANIER*\n\n"
        + cart_lines(cart)
        + f"\n💰 *Total panier : {sub}€*\n"
    )
    buttons = [
        [InlineKeyboardButton("🚀  Continuer vers la livraison", callback_data="go_delivery")],
        [InlineKeyboardButton("➕  Ajouter un autre produit",    callback_data="go_catalogue")],
        [InlineKeyboardButton("🗑️  Vider le panier",             callback_data="clear_cart")],
        [back_btn("go_catalogue")],
    ]
    if from_msg:
        await update.message.reply_text(msg, reply_markup=kb(buttons), parse_mode="Markdown")
    else:
        try:
            await update.callback_query.edit_message_text(msg, reply_markup=kb(buttons), parse_mode="Markdown")
        except Exception:
            await update.effective_message.reply_text(msg, reply_markup=kb(buttons), parse_mode="Markdown")
    return CART_STATE


async def cart_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "clear_cart":
        ctx.user_data["cart"] = []
        return await show_catalogue(update, ctx)
    if q.data == "go_delivery":
        return await show_delivery(update, ctx)
    if q.data == "go_catalogue":
        return await show_catalogue(update, ctx)
    if q.data == "resume_cart":
        return await show_cart(update, ctx)
    return CART_STATE


# ═══════════════════════════════════════════
# PAGE 5 — ÉTAPE 3/5 LIVRAISON
# ═══════════════════════════════════════════
async def show_delivery(update, ctx):
    q = update.callback_query
    msg = (
        f"{sep()}\n"
        "🧭 *Étape 3/5 — Livraison*\n\n"
        "Choisissez votre mode de livraison :\n"
    )
    buttons = [
        [InlineKeyboardButton("🤝  Main propre — GRATUIT (Île de France)", callback_data="del_main")],
        [InlineKeyboardButton(f"🇫🇷  Livraison France — {FRAIS_FR}€ ( 1 à 3 jours )", callback_data="del_fr")],
        [InlineKeyboardButton(f"🌍  Livraison Europe — {FRAIS_EU}€ ( 4 à 6 jours )", callback_data="del_eu")],
        [back_btn("back_to_cart")],
    ]
    await q.edit_message_text(msg, reply_markup=kb(buttons), parse_mode="Markdown")
    return DELIVERY_STATE


async def set_delivery(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "back_to_cart":
        return await show_cart(update, ctx)
    if q.data == "del_main":
        ctx.user_data["frais"] = FRAIS_MAIN
        ctx.user_data["zone"]  = "🤝 Remise en main propre (Île de France)"
    elif q.data == "del_fr":
        ctx.user_data["frais"] = FRAIS_FR
        ctx.user_data["zone"]  = "🇫🇷 France"
    else:
        ctx.user_data["frais"] = FRAIS_EU
        ctx.user_data["zone"]  = "🌍 Europe"
    return await ask_fname(update, ctx)


# ═══════════════════════════════════════════
# PAGE 6 — ÉTAPE 4/5 INFORMATIONS
# ═══════════════════════════════════════════
async def ask_fname(update, ctx):
    msg = (
        f"{sep()}\n"
        "📋 *VOS INFORMATIONS DE LIVRAISON*\n\n"
        "Votre *prénom* :\n_(Tapez votre prénom)_\n\n"
    )
    buttons = [[help_btn(), back_btn("back_to_delivery")]]
    try:
        await update.callback_query.edit_message_text(msg, reply_markup=kb(buttons), parse_mode="Markdown")
    except Exception:
        await update.effective_message.reply_text(msg, reply_markup=kb(buttons), parse_mode="Markdown")
    return INFO_FNAME


async def get_fname(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        if update.callback_query.data == "back_to_delivery":
            return await show_delivery_from_callback(update, ctx)
        return INFO_FNAME
    v = update.message.text.strip()
    if len(v) < 2:
        await update.message.reply_text("⚠️ Prénom invalide. Réessayez :")
        return INFO_FNAME
    ctx.user_data["fname"] = v
    buttons = [[help_btn(), back_btn("back_to_fname")]]
    await update.message.reply_text(
        "✅ Prénom enregistré : *" + v + "*\n\nVotre *nom de famille* :",
        reply_markup=kb(buttons), parse_mode="Markdown",
    )
    return INFO_LNAME


async def get_lname(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        if update.callback_query.data == "back_to_fname":
            ctx.user_data.pop("fname", None)
            return await ask_fname(update, ctx)
        return INFO_LNAME
    v = update.message.text.strip()
    if len(v) < 2:
        await update.message.reply_text("⚠️ Nom invalide. Réessayez :")
        return INFO_LNAME
    ctx.user_data["lname"] = v
    buttons = [[help_btn(), back_btn("back_to_fname")]]

    if ctx.user_data.get("zone") == "🤝 Remise en main propre (Île de France)":
        ctx.user_data["address"] = "Remise en main propre"
        await update.message.reply_text(
            "✅ Nom enregistré : *" + v + "*\n\n"
            "🤝 Pour la remise en main propre, notre équipe vous contactera "
            "directement pour fixer le lieu et l'heure du rendez-vous.\n\n"
            "Votre *numéro de téléphone* :\n"
            "_(C'est par ce numéro que nous vous contacterons)_",
            reply_markup=kb(buttons), parse_mode="Markdown",
        )
        return INFO_PHONE

    await update.message.reply_text(
        "✅ Nom enregistré : *" + v + "*\n\nVotre *adresse complète* :\n_(Numéro, rue, code postal, ville, pays)_",
        reply_markup=kb(buttons), parse_mode="Markdown",
    )
    return INFO_ADDRESS


async def get_address(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        if update.callback_query.data == "back_to_fname":
            ctx.user_data.pop("lname", None)
            buttons = [[help_btn(), back_btn("back_to_delivery")]]
            await update.callback_query.edit_message_text(
                f"{sep()}\nVotre *prénom* :\n_(Tapez votre prénom)_",
                reply_markup=kb(buttons), parse_mode="Markdown",
            )
            return INFO_FNAME
        return INFO_ADDRESS
    v = update.message.text.strip()
    if len(v) < 10:
        await update.message.reply_text("⚠️ Adresse trop courte. Entrez l'adresse complète :")
        return INFO_ADDRESS
    ctx.user_data["address"] = v
    buttons = [[help_btn(), back_btn("back_to_lname")]]
    await update.message.reply_text(
        "✅ Adresse enregistrée !\n\nVotre *numéro de téléphone* :",
        reply_markup=kb(buttons), parse_mode="Markdown",
    )
    return INFO_PHONE


async def get_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        if update.callback_query.data == "back_to_lname":
            ctx.user_data.pop("address", None)
            buttons = [[help_btn(), back_btn("back_to_fname")]]
            await update.callback_query.edit_message_text(
                "✅ Prénom : *" + ctx.user_data.get("fname","") + "*\n\nVotre *nom de famille* :",
                reply_markup=kb(buttons), parse_mode="Markdown",
            )
            return INFO_LNAME
        return INFO_PHONE
    v = update.message.text.strip()
    if len([c for c in v if c.isdigit()]) < 8:
        await update.message.reply_text("⚠️ Numéro invalide. Réessayez (ex: 06 12 34 56 78) :")
        return INFO_PHONE
    ctx.user_data["phone"] = v
    await update.message.reply_text("✅ Téléphone enregistré : *" + v + "*", parse_mode="Markdown")

    if ctx.user_data.get("zone") == "🤝 Remise en main propre (Île de France)":
        return await ask_payment_method(update, ctx)
    return await show_recap(update, ctx)


# ═══════════════════════════════════════════
# CHOIX PAIEMENT (remise en main propre)
# ═══════════════════════════════════════════
async def ask_payment_method(update, ctx):
    msg = (
        f"{sep()}\n"
        "💳 *Comment souhaitez-vous payer ?*\n"
    )
    buttons = [
        [InlineKeyboardButton("💵  Payer sur place",  callback_data="pay_place")],
        [InlineKeyboardButton("💳  Payer en ligne",   callback_data="pay_online")],
        [back_btn("back_to_phone")],
    ]
    await update.message.reply_text(msg, reply_markup=kb(buttons), parse_mode="Markdown")
    return PAYMENT_METHOD_MAIN


async def choose_payment_method(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "back_to_phone":
        ctx.user_data.pop("phone", None)
        buttons = [[help_btn(), back_btn("back_to_lname")]]
        await q.edit_message_text(
            "Votre *numéro de téléphone* :",
            reply_markup=kb(buttons), parse_mode="Markdown",
        )
        return INFO_PHONE
    ctx.user_data["pay_method"] = q.data
    if q.data == "pay_place":
        return await show_confirmation_main(update, ctx)
    else:
        return await show_recap(update, ctx)


# ═══════════════════════════════════════════
# CONFIRMATION PAIEMENT SUR PLACE
# ═══════════════════════════════════════════
async def show_confirmation_main(update, ctx):
    d = ctx.user_data
    cart = d.get("cart", [])
    frais = d.get("frais", 0)
    sub, total = cart_total(cart, frais)
    ref = d.setdefault("ref", gen_ref())
    cancel_reminder(ctx, update.effective_user.id)
    msg = (
        f"{sep()}\n"
        "✅ *Commande enregistrée !*\n\n"
        "📋 *RÉCAPITULATIF*\n\n"
        + cart_lines(cart)
        + f"🚚 {d.get('zone','')} : {frais}€\n"
        f"💰 *Total : {total}€*\n"
        f"🎫 Référence : `{ref}`\n\n"
        f"{sep()}\n"
        f"👤 {d.get('fname','')} {d.get('lname','')}\n"
        f"📞 {d.get('phone','')}\n\n"
        f"{sep()}\n"
        "📌 *Pour la remise en main propre, notre équipe vous contactera "
        "au plus vite afin de fixer le lieu et la date de rendez-vous.*"
    )
    buttons = [[help_btn()]]
    try:
        await update.callback_query.edit_message_text(msg, reply_markup=kb(buttons), parse_mode="Markdown")
    except Exception:
        await update.effective_message.reply_text(msg, reply_markup=kb(buttons), parse_mode="Markdown")
    await notify_admin(update, ctx, total, ref, frais)
    return ConversationHandler.END


# ═══════════════════════════════════════════
# PAGE 7 — ÉTAPE 5/5 RÉCAPITULATIF
# ═══════════════════════════════════════════
async def show_recap(update, ctx):
    d = ctx.user_data
    cart = d.get("cart", [])
    frais = d.get("frais", FRAIS_FR)
    sub, total = cart_total(cart, frais)
    msg = (
        f"{sep()}\n"
        "🧭 *Étape 5/5 — Validation*\n\n"
        f"💰 *MONTANT À PAYER : {total}€*\n\n"
        "📋 *RÉCAPITULATIF DE COMMANDE*\n\n"
        "📦 *Produits :*\n"
        + cart_lines(cart)
        + f"🚚 Livraison {d.get('zone','')} : {frais}€\n\n"
        f"{sep()}\n"
        f"👤 {d.get('fname','')} {d.get('lname','')}\n"
        + (f"📍 {d.get('address','')}\n" if d.get('address') != "Remise en main propre" else "")
        + f"📞 {d.get('phone','')}\n"
    )
    buttons = [
        [InlineKeyboardButton(f"💳  Confirmer & Payer {total}€", callback_data="go_payment")],
        [InlineKeyboardButton("📍  Modifier adresse",   callback_data="mod_address"),
         InlineKeyboardButton("📞  Modifier téléphone", callback_data="mod_phone")],
        [InlineKeyboardButton("🛒  Modifier mes produits", callback_data="go_catalogue")],
        [back_btn("back_to_phone"),
         InlineKeyboardButton("❌  Annuler", callback_data="go_home")],
        [help_btn()],
    ]
    try:
        await update.message.reply_text(msg, reply_markup=kb(buttons), parse_mode="Markdown")
    except Exception:
        await update.callback_query.edit_message_text(msg, reply_markup=kb(buttons), parse_mode="Markdown")
    return RECAP_STATE


async def recap_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "go_payment":
        return await show_payment(update, ctx)
    if q.data == "back_to_phone":
        ctx.user_data.pop("phone", None)
        buttons = [[help_btn(), back_btn("back_to_lname")]]
        await q.edit_message_text(
            "Votre *numéro de téléphone* :",
            reply_markup=kb(buttons), parse_mode="Markdown",
        )
        return INFO_PHONE
    if q.data == "mod_address":
        ctx.user_data.pop("address", None)
        await q.edit_message_text(
            f"{sep()}\n📍 Entrez votre *nouvelle adresse* :\n_(Numéro, rue, code postal, ville, pays)_",
            reply_markup=kb([[help_btn(), back_btn("back_to_lname")]]), parse_mode="Markdown",
        )
        return INFO_ADDRESS
    if q.data == "mod_phone":
        ctx.user_data.pop("phone", None)
        await q.edit_message_text(
            f"{sep()}\n📞 Entrez votre *nouveau numéro de téléphone* :",
            reply_markup=kb([[help_btn(), back_btn("back_to_lname")]]), parse_mode="Markdown",
        )
        return INFO_PHONE
    if q.data == "go_catalogue":
        return await show_catalogue(update, ctx)
    if q.data == "go_home":
        return await start(update, ctx)
    return RECAP_STATE


# ═══════════════════════════════════════════
# PAGE 8 — PAIEMENT
# ═══════════════════════════════════════════
async def show_payment(update, ctx):
    d = ctx.user_data
    cart = d.get("cart", [])
    frais = d.get("frais", FRAIS_FR)
    sub, total = cart_total(cart, frais)
    ref = d.setdefault("ref", gen_ref())
    is_main = d.get("zone") == "🤝 Remise en main propre (Île de France)"

    msg = (
        f"{sep()}\n"
        "💳 *PAIEMENT SÉCURISÉ*\n\n"
        f"💰 Montant à régler : *{total}€*\n"
        f"🎫 Référence : `{ref}`\n\n"
        "*Sur la page de paiement, choisissez :*\n\n"
        "🔵 *MoonPay* → PayPal, carte bancaire, Apple Pay, Google Pay\n"
        "🔄 *Revolut* → disponible via le bouton Revolut\n"
        "🌑 *Crypto* → directement disponible\n\n"
        "👇 *Cliquez sur le bouton pour payer*\n"
        "💡 _En cas de problème, ouvrez le lien dans Safari, Chrome ou Firefox._"
    )

    if PAYMENT_LINK:
        pay_btn = InlineKeyboardButton(f"💳  Payer {total}€", url=PAYMENT_LINK)
    else:
        pay_btn = InlineKeyboardButton(f"💳  Payer {total}€ — Lien bientôt disponible", callback_data="no_link")

    buttons = [
        [pay_btn],
        [help_btn(), back_btn("back_to_recap")],
    ]

    try:
        await update.callback_query.edit_message_text(msg, reply_markup=kb(buttons), parse_mode="Markdown")
    except Exception:
        await update.effective_message.reply_text(msg, reply_markup=kb(buttons), parse_mode="Markdown")

    # Sauvegarde commande en attente pour webhook Nexapay
    ctx.bot_data.setdefault("pending_orders", {})[ref] = {
        "chat_id": update.effective_chat.id,
        "user_id": update.effective_user.id,
        "username": update.effective_user.username or "—",
        "fname": ctx.user_data.get("fname",""),
        "lname": ctx.user_data.get("lname",""),
        "phone": ctx.user_data.get("phone",""),
        "address": ctx.user_data.get("address",""),
        "zone": ctx.user_data.get("zone",""),
        "cart": ctx.user_data.get("cart",[]),
        "total": total,
        "frais": frais,
        "ref": ref,
    }
    # Notif admin envoyée uniquement après confirmation Nexapay (voir confirm_payment_webhook)
    return PAYMENT_STATE


async def payment_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "back_to_recap":
        return await show_recap(update, ctx)
    if q.data == "no_link":
        await q.answer("Lien de paiement bientôt disponible — contactez @serenovalabsupport", show_alert=True)
        return PAYMENT_STATE
    if q.data == "paid_online":
        cancel_reminder(ctx, update.effective_user.id)
        return await show_thank_you(update, ctx)
    return PAYMENT_STATE


# ═══════════════════════════════════════════
# MESSAGE REMERCIEMENT
# ═══════════════════════════════════════════
async def show_thank_you(update, ctx):
    d = ctx.user_data
    is_main = d.get("zone") == "🤝 Remise en main propre (Île de France)"
    ref = d.get("ref", "—")
    cart = d.get("cart", [])
    frais = d.get("frais", FRAIS_FR)
    sub, total = cart_total(cart, frais)

    msg = (
        f"{sep()}\n"
        "✅ *Paiement confirmé !*\n\n"
        f"🎫 La commande *{ref}* a bien été payée.\n\n"
        f"💰 Montant réglé : *{total}€*\n\n"
        f"{sep()}\n"
        "🙏 *Serenova vous remercie pour votre confiance.*\n"
        "Votre commande sera traitée au plus vite !\n"
    )
    if is_main:
        msg += (
            f"\n{sep()}\n"
            "📌 *Notre équipe vous contactera au plus vite "
            "afin de fixer le lieu et la date de rendez-vous.*"
        )
    else:
        msg += (
            f"\n{sep()}\n"
            "📦 *Votre commande sera expédiée sous 24h !*"
        )
    buttons = [
        [help_btn()],
        [InlineKeyboardButton("🏠  Retour à l'accueil", callback_data="go_home")],
    ]
    await update.callback_query.edit_message_text(msg, reply_markup=kb(buttons), parse_mode="Markdown")
    return ConversationHandler.END


# ═══════════════════════════════════════════
# NOTIF ADMIN
# ═══════════════════════════════════════════
async def notify_admin(update, ctx, total, ref, frais):
    d    = ctx.user_data
    cart = d.get("cart", [])
    user = update.effective_user
    pay  = "Sur place" if d.get("pay_method") == "pay_place" else "En ligne"
    admin_msg = (
        "🔔 *NOUVELLE COMMANDE — Serenova*\n"
        f"{sep()}\n"
        + cart_lines(cart)
        + f"🚚 {d.get('zone','')} : {frais}€\n"
        f"💰 *Total : {total}€*\n"
        f"🎫 Référence : `{ref}`\n"
        f"{sep()}\n"
        f"👤 {d.get('fname','')} {d.get('lname','')}\n"
        + (f"📍 {d.get('address','')}\n" if d.get('address') != "Remise en main propre" else "")
        + f"📞 {d.get('phone','')}\n"
        f"📱 @{user.username or '—'} (ID: {user.id})\n"
        f"💳 Paiement : {pay}\n"
    )
    try:
        await ctx.bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Admin notif failed: {e}")


async def show_delivery_from_callback(update, ctx):
    q = update.callback_query
    msg = (
        f"{sep()}\n"
        "🧭 *Étape 3/5 — Livraison*\n\n"
        "Choisissez votre mode de livraison :\n"
    )
    buttons = [
        [InlineKeyboardButton("🤝  Remise en main propre — GRATUIT (Île de France)", callback_data="del_main")],
        [InlineKeyboardButton(f"🇫🇷  Livraison France — {FRAIS_FR}€ ( 1 à 3 jours )", callback_data="del_fr")],
        [InlineKeyboardButton(f"🌍  Livraison Europe — {FRAIS_EU}€ ( 4 à 6 jours )", callback_data="del_eu")],
        [back_btn("back_to_cart")],
    ]
    await q.edit_message_text(msg, reply_markup=kb(buttons), parse_mode="Markdown")
    return DELIVERY_STATE


# ═══════════════════════════════════════════
# ANNULATION + HOME
# ═══════════════════════════════════════════
async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cancel_reminder(ctx, update.effective_user.id)
    ctx.user_data.clear()
    await update.message.reply_text(
        f"{sep()}\n🚫 Commande annulée.\nTapez /start pour recommencer.",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def home_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    return await start(update, ctx)


# ═══════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════

# ═══════════════════════════════════════════
# CONFIRMATION PAIEMENT (déclenché par webhook Nexapay)
# À appeler quand Nexapay confirme le paiement
# ═══════════════════════════════════════════
async def confirm_payment_webhook(application, ref: str):
    """
    Appelé par le webhook Nexapay quand un paiement est confirmé.
    ref = référence de commande (ex: SRN-A4B2C8)
    """
    orders = application.bot_data.get("pending_orders", {})
    order  = orders.get(ref)
    if not order:
        logging.warning(f"Commande {ref} introuvable dans pending_orders")
        return

    chat_id  = order["chat_id"]
    total    = order["total"]
    zone     = order.get("zone", "")
    is_main  = zone == "🤝 Remise en main propre (Île de France)"

    # Message client
    msg_client = (
        f"{sep()}\n"
        "✅ *Paiement confirmé !*\n\n"
        f"🎫 La commande *{ref}* a bien été payée.\n\n"
        f"💰 Montant réglé : *{total}€*\n\n"
        f"{sep()}\n"
        "🙏 *Serenova vous remercie pour votre confiance.*\n"
        "Votre commande sera traitée au plus vite !\n"
    )
    if is_main:
        msg_client += (
            f"\n{sep()}\n"
            "✅ *Paiement bien reçu !*\n"
            "📌 *Notre équipe vous contactera au plus vite "
            "afin de fixer le lieu et la date de rendez-vous.*"
        )
    else:
        msg_client += (
            f"\n{sep()}\n"
            "📦 *Votre commande sera expédiée sous 24h !*"
        )

    # Message admin
    msg_admin = (
        f"💳 *PAIEMENT CONFIRMÉ — Serenova*\n"
        f"{sep()}\n"
        f"🎫 Référence : `{ref}`\n"
        f"💰 Montant : *{total}€*\n"
        f"{sep()}\n"
        f"👤 {order.get('fname','')} {order.get('lname','')}\n"
        f"📍 {order.get('address','')}\n"
        f"📞 {order.get('phone','')}\n"
        f"📱 @{order.get('username','—')}\n"
        f"🚚 {zone}\n"
    )

    try:
        await application.bot.send_message(chat_id, msg_client, parse_mode="Markdown")
        await application.bot.send_message(ADMIN_ID, msg_admin, parse_mode="Markdown")
        # Supprimer commande en attente
        orders.pop(ref, None)
        logging.info(f"Paiement confirmé pour {ref}")
    except Exception as e:
        logging.error(f"Erreur confirmation {ref}: {e}")

# ═══════════════════════════════════════════
# TODO — Quand tu as l'API Nexapay :
# 1. Crée un endpoint HTTP qui reçoit les webhooks Nexapay
# 2. Parse la référence de commande depuis le payload
# 3. Appelle : await confirm_payment_webhook(application, ref)
# ═══════════════════════════════════════════

def main():
    while True:
        try:
            app = Application.builder().token(TOKEN).build()
            conv = ConversationHandler(
                entry_points=[CommandHandler("start", start)],
                states={
                    HOME: [
                        CallbackQueryHandler(show_catalogue, pattern="^go_catalogue$"),
                        CallbackQueryHandler(home_handler,   pattern="^go_home$"),
                    ],
                    CATALOGUE_STATE: [
                        CallbackQueryHandler(show_product,   pattern="^prod_"),
                        CallbackQueryHandler(home_handler,   pattern="^go_home$"),
                    ],
                    QUANTITY_STATE: [
                        CallbackQueryHandler(set_quantity,   pattern="^qty_"),
                        CallbackQueryHandler(show_catalogue, pattern="^go_catalogue$"),
                    ],
                    CUSTOM_QTY: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, custom_quantity),
                        CallbackQueryHandler(show_catalogue, pattern="^go_catalogue$"),
                    ],
                    SERINGUE_STATE: [
                        CallbackQueryHandler(seringue_handler, pattern="^seringue_"),
                    ],
                    CART_STATE: [
                        CallbackQueryHandler(cart_handler),
                    ],
                    DELIVERY_STATE: [
                        CallbackQueryHandler(set_delivery),
                    ],
                    PAYMENT_METHOD_MAIN: [
                        CallbackQueryHandler(choose_payment_method),
                    ],
                    INFO_FNAME: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, get_fname),
                        CallbackQueryHandler(get_fname, pattern="^back_"),
                    ],
                    INFO_LNAME: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, get_lname),
                        CallbackQueryHandler(get_lname, pattern="^back_"),
                    ],
                    INFO_ADDRESS: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, get_address),
                        CallbackQueryHandler(get_address, pattern="^back_"),
                    ],
                    INFO_PHONE: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone),
                        CallbackQueryHandler(get_phone, pattern="^back_"),
                    ],
                    RECAP_STATE:   [CallbackQueryHandler(recap_handler)],
                    PAYMENT_STATE: [CallbackQueryHandler(payment_handler)],
                },
                fallbacks=[CommandHandler("annuler", cancel), CommandHandler("start", start)],
                allow_reentry=True,
            )
            app.add_handler(conv)
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print("  SERENOVA Bot v3 Final — En ligne ✅")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            app.run_polling(allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            logging.error(f"Erreur : {e}")
            print("⚠️  Reconnexion dans 10 secondes...")
            time.sleep(10)
            print("🔄  Redémarrage...")


if __name__ == "__main__":
    main()
