s = state(uid, tg_lang)
    await update.message.reply_text(
        "📄 ابعت PDF وأنا هعمل:\n"
        "✅ ملخص للطلاب\n"
        "🎧 بودكاست حواري MP3\n\n"
        "🌍 اللغات: ar / en / fr / de\n"
        "غيّر اللغة: /lang ar (أو en/fr/de)\n"
        f"اللغة الحالية: {s['lang']}"
    )

async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    s = state(uid, update.effective_user.language_code)
    if not context.args or context.args[0].lower() not in SUPPORTED:
        await update.message.reply_text("اكتب: /lang ar أو /lang en أو /lang fr أو /lang de")
        return
    s["lang"] = context.args[0].lower()
    await update.message.reply_text(f"تم ✅ اللغة الحالية: {s['lang']}")

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    s = state(uid, update.effective_user.language_code)

    doc = update.message.document
    if not doc or not (doc.file_name or "").lower().endswith(".pdf"):
        await update.message.reply_text("ابعث PDF فقط في المرحلة A.")
        return

    await update.message.reply_text("تمام… بتحميل الـ PDF ثم تلخيصه وتحويله لبودكاست 🎛️")

    tg_file = await doc.get_file()
    jid = str(uuid.uuid4())[:8]
    pdf_path = TMP / f"{uid}_{jid}.pdf"
    await tg_file.download_to_drive(custom_path=str(pdf_path))

    try:
        text = extract_text_from_pdf(pdf_path)
    except Exception as e:
        await update.message.reply_text(f"فشل قراءة PDF: {e}")
        return

    if not text:
        await update.message.reply_text("الـ PDF ده غالبًا سكان/صور ومفيهوش نص. (OCR هنضيفه بعدين).")
        return

    parts = chunk_text(text)
    summaries = []
    for i, part in enumerate(parts, start=1):
        await update.message.reply_text(f"تلخيص جزء {i}/{len(parts)}…")
        summaries.append(make_student_summary(part, s["lang"]))
    summary = "\n\n".join(summaries)

    await update.message.reply_text("✅ الملخص جاهز (هارسله على دفعات لو طويل)")
    for i in range(0, len(summary), 3500):
        await update.message.reply_text(summary[i:i+3500])

    await update.message.reply_text("بجهز سكريبت بودكاست حواري…")
    script = make_dialog_script(summary, s["lang"])

    # لتفادي حدود TTS
    script = script[:12000] if len(script) > 12000 else script
    out_mp3 = TMP / f"{uid}_{jid}.mp3"

    await update.message.reply_text("تحويل إلى MP3…")
    try:
        await tts_mp3(script, out_mp3, s["lang"])
    except Exception as e:
        await update.message.reply_text(f"فشل تحويل الصوت: {e}")
        return

    await update.message.reply_audio(audio=open(out_mp3, "rb"), title="podcast.mp3")
    await update.message.reply_text("تم ✅")

def main():
    if not BOT_TOKEN:
        raise RuntimeError("Missing BOT_TOKEN")
    if not GEMINI_API_KEY:
        raise RuntimeError("Missing GEMINI_API_KEY")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lang", lang_cmd))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))

    app.run_polling()

if name == "main":
    main()
