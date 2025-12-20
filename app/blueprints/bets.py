"""Betting routes for match wagering."""
import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_babel import get_locale
from flask_login import login_required, current_user
from app.extensions import db
from app.models import (
    Match, Team, Bet, AIBet, BetNotification, BetType, BetStatus,
    MAX_BET_AMOUNT, BET_PAYOUTS
)
from app.forms.bet import PlaceBetForm, AIBetForm, AIBetConfirmForm

bets_bp = Blueprint("bets", __name__, url_prefix="/bets")


@bets_bp.route("/")
@login_required
def index():
    """View all bets for the current user."""
    # Get user's bets, most recent first
    bets = Bet.query.filter_by(user_id=current_user.id).order_by(Bet.placed_at.desc()).all()
    
    # Separate pending and resolved bets
    pending_bets = [b for b in bets if b.status == BetStatus.PENDING]
    resolved_bets = [b for b in bets if b.status != BetStatus.PENDING]
    
    # Calculate stats
    total_won = sum(b.payout for b in bets if b.status == BetStatus.WON)
    total_lost = sum(b.amount for b in bets if b.status == BetStatus.LOST)
    total_pending = sum(b.amount for b in pending_bets)
    
    return render_template(
        "bets/index.html",
        pending_bets=pending_bets,
        resolved_bets=resolved_bets,
        total_won=total_won,
        total_lost=total_lost,
        total_pending=total_pending
    )


@bets_bp.route("/match/<int:match_id>", methods=["GET", "POST"])
@login_required
def place_bet(match_id: int):
    """Place a bet on a match."""
    match = Match.query.get_or_404(match_id)
    lang = session.get('language', 'en')
    
    # Check if match is already completed
    if match.status == "completed":
        if lang == 'es':
            flash("No puedes apostar en un partido que ya ha terminado.", "danger")
        else:
            flash("You cannot bet on a match that has already ended.", "danger")
        return redirect(url_for("matches.view", match_id=match_id))
    
    # Check if user owns one of the teams in the match
    user_team_ids = [t.id for t in current_user.teams]
    if match.home_team_id in user_team_ids or match.away_team_id in user_team_ids:
        if lang == 'es':
            flash("No puedes apostar en partidos donde participa tu equipo.", "danger")
        else:
            flash("You cannot bet on matches where your team is playing.", "danger")
        return redirect(url_for("matches.view", match_id=match_id))
    
    # Check if user already has a bet on this match
    existing_bet = Bet.query.filter_by(user_id=current_user.id, match_id=match_id).first()
    if existing_bet:
        if lang == 'es':
            flash("Ya tienes una apuesta en este partido.", "warning")
        else:
            flash("You already have a bet on this match.", "warning")
        return redirect(url_for("bets.view_bet", bet_id=existing_bet.id))
    
    form = PlaceBetForm()
    form.team_id.choices = [
        (match.home_team_id, match.home_team.name),
        (match.away_team_id, match.away_team.name)
    ]
    
    if form.validate_on_submit():
        bet_type = form.bet_type.data
        team_id = form.team_id.data
        amount = form.amount.data
        target_value = form.target_value.data if bet_type != BetType.WIN else None
        
        # Create the bet
        bet = Bet(
            user_id=current_user.id,
            match_id=match_id,
            bet_type=bet_type,
            team_id=team_id,
            target_value=target_value,
            amount=amount,
            status=BetStatus.PENDING
        )
        db.session.add(bet)
        db.session.commit()
        
        multiplier = BET_PAYOUTS.get(bet_type, 1)
        potential = amount * multiplier
        
        if lang == 'es':
            flash(f"¡Apuesta realizada! Apostaste {amount:,}g. Ganancia potencial: {potential:,}g", "success")
        else:
            flash(f"Bet placed! You wagered {amount:,}g. Potential win: {potential:,}g", "success")
        
        return redirect(url_for("bets.view_bet", bet_id=bet.id))
    
    return render_template(
        "bets/place_bet.html",
        form=form,
        match=match,
        max_bet=MAX_BET_AMOUNT,
        payouts=BET_PAYOUTS
    )


@bets_bp.route("/<int:bet_id>")
@login_required
def view_bet(bet_id: int):
    """View a specific bet."""
    bet = Bet.query.get_or_404(bet_id)
    
    # Only allow viewing own bets (or admin)
    if bet.user_id != current_user.id and not current_user.is_admin:
        if str(get_locale()) == 'es':
            flash("Solo puedes ver tus propias apuestas.", "danger")
        else:
            flash("You can only view your own bets.", "danger")
        return redirect(url_for("bets.index"))
    
    return render_template("bets/view_bet.html", bet=bet, payouts=BET_PAYOUTS)


@bets_bp.route("/<int:bet_id>/cancel", methods=["POST"])
@login_required
def cancel_bet(bet_id: int):
    """Cancel a pending bet."""
    bet = Bet.query.get_or_404(bet_id)
    lang = session.get('language', 'en')
    
    # Only allow canceling own bets
    if bet.user_id != current_user.id and not current_user.is_admin:
        if str(get_locale()) == 'es':
            flash("Solo puedes cancelar tus propias apuestas.", "danger")
        else:
            flash("You can only cancel your own bets.", "danger")
        return redirect(url_for("bets.index"))
    
    # Only allow canceling pending bets
    if bet.status != BetStatus.PENDING:
        if lang == 'es':
            flash("Solo puedes cancelar apuestas pendientes.", "warning")
        else:
            flash("You can only cancel pending bets.", "warning")
        return redirect(url_for("bets.view_bet", bet_id=bet_id))
    
    # Delete the bet
    db.session.delete(bet)
    db.session.commit()
    
    if lang == 'es':
        flash("Apuesta cancelada.", "success")
    else:
        flash("Bet cancelled.", "success")
    
    return redirect(url_for("bets.index"))


@bets_bp.route("/notifications")
@login_required
def notifications():
    """View bet notifications."""
    # Get unread notifications
    notifications = BetNotification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).order_by(BetNotification.created_at.desc()).all()
    
    return render_template("bets/notifications.html", notifications=notifications)


@bets_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_notification_read(notification_id: int):
    """Mark a notification as read."""
    notification = BetNotification.query.get_or_404(notification_id)
    
    if notification.user_id != current_user.id:
        return redirect(url_for("bets.notifications"))
    
    notification.mark_as_read()
    db.session.commit()
    
    return redirect(url_for("bets.notifications"))


@bets_bp.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read."""
    BetNotification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).update({"is_read": True})
    db.session.commit()
    
    lang = session.get('language', 'en')
    if lang == 'es':
        flash("Todas las notificaciones marcadas como leídas.", "success")
    else:
        flash("All notifications marked as read.", "success")
    
    return redirect(url_for("bets.index"))


def resolve_match_bets(match):
    """
    Resolve all STANDARD bets for a completed match.
    Called when match results are recorded.
    Note: AI bets (bet_type='ai_custom') are resolved separately via manual confirmation.
    """
    # Get all pending STANDARD bets for this match (exclude AI bets)
    pending_bets = Bet.query.filter(
        Bet.match_id == match.id,
        Bet.status == BetStatus.PENDING,
        Bet.bet_type != "ai_custom"
    ).all()
    
    for bet in pending_bets:
        # Resolve the bet
        bet.resolve(match)
        
        # Create notification
        notification = BetNotification(
            user_id=bet.user_id,
            bet_id=bet.id
        )
        db.session.add(notification)
    
    db.session.commit()
    return len(pending_bets)


def get_pending_ai_bets(match):
    """Get all pending AI bets for a match that need manual confirmation."""
    return AIBet.query.filter(
        AIBet.match_id == match.id,
        AIBet.status == BetStatus.PENDING,
        AIBet.bet_type == "ai_custom"
    ).all()


def resolve_ai_bet(bet, is_won: bool, lang: str = "en"):
    """
    Resolve an AI bet based on manual confirmation.
    
    Args:
        bet: The AI bet to resolve
        is_won: Whether the bet prediction came true
        lang: Language for notification message
    """
    from datetime import datetime
    
    bet.resolved_at = datetime.utcnow()
    
    if is_won:
        bet.status = BetStatus.WON
        bet.payout = int(bet.amount * bet.multiplier)
        # Add winnings to user's treasury (if user has a team, add to their first team)
        # For now, we'll just track the payout
    else:
        bet.status = BetStatus.LOST
        bet.payout = 0
    
    # Extract bet description from rationale
    bet_description = ""
    if bet.ai_rationale and "Bet:" in bet.ai_rationale:
        bet_description = bet.ai_rationale.split("Bet:")[1].split("Analysis:")[0].strip()
    else:
        bet_description = "AI custom bet"
    
    # Create notification
    match = bet.match
    home_team = match.home_team.name
    away_team = match.away_team.name
    match_result = f"{home_team} {match.home_score} - {match.away_score} {away_team}"
    
    if lang == "es":
        if bet.status == BetStatus.WON:
            message = (
                f"🎉 ¡Ganaste tu apuesta IA! Tu predicción se cumplió: \"{bet_description}\" "
                f"({match_result}). "
                f"Apostaste {bet.amount:,}g y ganaste {bet.payout:,}g."
            )
        else:
            message = (
                f"😞 Perdiste tu apuesta IA. Tu predicción no se cumplió: \"{bet_description}\" "
                f"({match_result}). "
                f"Perdiste {bet.amount:,}g."
            )
    else:
        if bet.status == BetStatus.WON:
            message = (
                f"🎉 You won your AI bet! Your prediction came true: \"{bet_description}\" "
                f"({match_result}). "
                f"You bet {bet.amount:,}g and won {bet.payout:,}g."
            )
        else:
            message = (
                f"😞 You lost your AI bet. Your prediction did not come true: \"{bet_description}\" "
                f"({match_result}). "
                f"You lost {bet.amount:,}g."
            )
    
    # Create custom notification with the message stored
    notification = BetNotification(
        user_id=bet.user_id,
        bet_id=bet.id
    )
    db.session.add(notification)
    
    return message


# =============================================================================
# AI Betting Routes
# =============================================================================

@bets_bp.route("/ai")
@login_required
def ai_bet_index():
    """Show form for creating an AI-powered bet."""
    lang = session.get('language', 'en')
    form = AIBetForm()
    
    # Get available matches (scheduled, where user doesn't own a team)
    user_team_ids = [t.id for t in current_user.teams]
    available_matches = Match.query.filter(
        Match.status == "scheduled",
        ~Match.home_team_id.in_(user_team_ids) if user_team_ids else True,
        ~Match.away_team_id.in_(user_team_ids) if user_team_ids else True
    ).order_by(Match.scheduled_date.asc()).all()
    
    # Filter out matches where user already has a bet
    user_bet_match_ids = [b.match_id for b in Bet.query.filter_by(user_id=current_user.id).all()]
    available_matches = [m for m in available_matches if m.id not in user_bet_match_ids]
    
    if not available_matches:
        if lang == 'es':
            flash("No hay partidos disponibles para apostar.", "warning")
        else:
            flash("No available matches to bet on.", "warning")
        return redirect(url_for("bets.index"))
    
    form.match_id.choices = [
        (m.id, f"{m.home_team.name} vs {m.away_team.name}")
        for m in available_matches
    ]
    
    # Check if a specific match was requested
    preselected_match_id = request.args.get('match_id', type=int)
    if preselected_match_id and preselected_match_id in [m.id for m in available_matches]:
        form.match_id.data = preselected_match_id
    
    return render_template(
        "bets/ai_bet.html",
        form=form,
        matches=available_matches,
        max_bet=MAX_BET_AMOUNT,
        preselected_match_id=preselected_match_id
    )


@bets_bp.route("/ai/match/<int:match_id>")
@login_required
def ai_bet_match(match_id: int):
    """Redirect to AI bet form with match pre-selected."""
    lang = session.get('language', 'en')
    match = Match.query.get_or_404(match_id)
    
    # Validate match is available for betting
    if match.status != "scheduled":
        if lang == 'es':
            flash("Este partido ya no está disponible para apuestas.", "danger")
        else:
            flash("This match is no longer available for betting.", "danger")
        return redirect(url_for("matches.view", match_id=match_id))
    
    # Check if user owns one of the teams
    user_team_ids = [t.id for t in current_user.teams]
    if match.home_team_id in user_team_ids or match.away_team_id in user_team_ids:
        if lang == 'es':
            flash("No puedes apostar en partidos donde participa tu equipo.", "danger")
        else:
            flash("You cannot bet on matches where your team is playing.", "danger")
        return redirect(url_for("matches.view", match_id=match_id))
    
    # Check if user already has a bet
    existing_bet = Bet.query.filter_by(user_id=current_user.id, match_id=match_id).first()
    if existing_bet:
        if lang == 'es':
            flash("Ya tienes una apuesta en este partido.", "warning")
        else:
            flash("You already have a bet on this match.", "warning")
        return redirect(url_for("bets.view_bet", bet_id=existing_bet.id))
    
    return redirect(url_for("bets.ai_bet_index", match_id=match_id))


@bets_bp.route("/ai/preview", methods=["POST"])
@login_required
def ai_bet_preview():
    """Preview the AI-calculated multiplier for a bet."""
    lang = session.get('language', 'en')
    form = AIBetForm()
    
    # Get available matches for form validation
    user_team_ids = [t.id for t in current_user.teams]
    available_matches = Match.query.filter(
        Match.status == "scheduled",
        ~Match.home_team_id.in_(user_team_ids) if user_team_ids else True,
        ~Match.away_team_id.in_(user_team_ids) if user_team_ids else True
    ).all()
    
    form.match_id.choices = [(m.id, f"{m.home_team.name} vs {m.away_team.name}") for m in available_matches]
    
    if not form.validate_on_submit():
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "danger")
        return redirect(url_for("bets.ai_bet_index"))
    
    match_id = form.match_id.data
    bet_description = form.bet_description.data
    amount = form.amount.data
    
    match = Match.query.get_or_404(match_id)
    
    # Check if user already has a bet on this match
    existing_bet = Bet.query.filter_by(user_id=current_user.id, match_id=match_id).first()
    if existing_bet:
        if lang == 'es':
            flash("Ya tienes una apuesta en este partido.", "warning")
        else:
            flash("You already have a bet on this match.", "warning")
        return redirect(url_for("bets.view_bet", bet_id=existing_bet.id))
    
    # Create a temporary AIBet to calculate the multiplier
    # We need to determine which team the bet is for based on the description
    # For AI bets, we'll use a custom bet type
    temp_bet = AIBet(
        user_id=current_user.id,
        match_id=match_id,
        bet_type="ai_custom",
        team_id=match.home_team_id,  # Default to home team, AI will analyze
        amount=amount,
        status=BetStatus.PENDING
    )
    
    # Store the bet description for the prompt
    temp_bet.bet_description_text = bet_description
    
    # Calculate the multiplier using LLM with custom description
    multiplier, rationale, confidence = _calculate_ai_multiplier(
        match, bet_description, amount, lang
    )
    
    # Store data for confirmation
    ai_bet_data = {
        "match_id": match_id,
        "bet_description": bet_description,
        "amount": amount,
        "multiplier": multiplier,
        "rationale": rationale,
        "confidence": confidence
    }
    
    confirm_form = AIBetConfirmForm()
    confirm_form.ai_bet_data.data = json.dumps(ai_bet_data)
    
    return render_template(
        "bets/ai_bet_preview.html",
        match=match,
        bet_description=bet_description,
        amount=amount,
        multiplier=multiplier,
        rationale=rationale,
        confidence=confidence,
        potential_payout=int(amount * multiplier),
        form=confirm_form
    )


@bets_bp.route("/ai/confirm", methods=["POST"])
@login_required
def ai_bet_confirm():
    """Confirm and place the AI bet."""
    lang = session.get('language', 'en')
    form = AIBetConfirmForm()
    
    if not form.validate_on_submit():
        if lang == 'es':
            flash("Envío de formulario inválido.", "danger")
        else:
            flash("Invalid form submission.", "danger")
        return redirect(url_for("bets.ai_bet_index"))
    
    try:
        ai_bet_data = json.loads(form.ai_bet_data.data)
    except json.JSONDecodeError:
        if lang == 'es':
            flash("Datos de apuesta inválidos.", "danger")
        else:
            flash("Invalid bet data.", "danger")
        return redirect(url_for("bets.ai_bet_index"))
    
    match_id = ai_bet_data["match_id"]
    bet_description = ai_bet_data["bet_description"]
    amount = ai_bet_data["amount"]
    multiplier = ai_bet_data["multiplier"]
    rationale = ai_bet_data["rationale"]
    confidence = ai_bet_data["confidence"]
    
    match = Match.query.get_or_404(match_id)
    
    # Validate match is still available
    if match.status != "scheduled":
        if lang == 'es':
            flash("Este partido ya no está disponible para apuestas.", "danger")
        else:
            flash("This match is no longer available for betting.", "danger")
        return redirect(url_for("bets.index"))
    
    # Check if user already has a bet
    existing_bet = Bet.query.filter_by(user_id=current_user.id, match_id=match_id).first()
    if existing_bet:
        if lang == 'es':
            flash("Ya tienes una apuesta en este partido.", "warning")
        else:
            flash("You already have a bet on this match.", "warning")
        return redirect(url_for("bets.view_bet", bet_id=existing_bet.id))
    
    # Create the AI bet
    ai_bet = AIBet(
        user_id=current_user.id,
        match_id=match_id,
        bet_type="ai_custom",
        team_id=match.home_team_id,  # AI bets don't target a specific team
        amount=amount,
        status=BetStatus.PENDING,
        ai_multiplier=multiplier,
        ai_rationale=rationale,
        ai_confidence=confidence
    )
    
    # Store the bet description in a custom field if available
    # For now, we'll include it in the rationale
    if not ai_bet.ai_rationale.startswith("Bet:"):
        ai_bet.ai_rationale = f"Bet: {bet_description}\n\nAnalysis: {rationale}"
    
    db.session.add(ai_bet)
    db.session.commit()
    
    potential = int(amount * multiplier)
    if lang == 'es':
        flash(f"¡Apuesta IA realizada! Apostaste {amount:,}g con multiplicador {multiplier:.2f}x. Ganancia potencial: {potential:,}g", "success")
    else:
        flash(f"AI Bet placed! You wagered {amount:,}g at {multiplier:.2f}x multiplier. Potential win: {potential:,}g", "success")
    
    return redirect(url_for("bets.view_bet", bet_id=ai_bet.id))


def _calculate_ai_multiplier(match, bet_description: str, amount: int, lang: str = "en") -> tuple[float, str, float]:
    """
    Calculate AI multiplier for a custom bet description.
    
    Args:
        match: The match object
        bet_description: User's bet description
        amount: Bet amount
        lang: Language for the response ('en' or 'es')
    
    Returns:
        Tuple of (multiplier, rationale, confidence)
    """
    import os
    
    try:
        from google import genai
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            if lang == 'es':
                return (AIBet.DEFAULT_MULTIPLIER, "Análisis IA no disponible (sin clave API)", 0.0)
            return (AIBet.DEFAULT_MULTIPLIER, "AI analysis unavailable (no API key)", 0.0)
        
        # Gather team data
        home_team = match.home_team
        away_team = match.away_team
        
        # Language-specific instructions
        if lang == 'es':
            language_instruction = """
IMPORTANTE: Responde completamente en ESPAÑOL. El campo "rationale" debe estar escrito en español."""
            task_description = """## Tarea
Estima un multiplicador de pago justo para esta apuesta. Considera:
1. ¿Qué tan específica/difícil es la predicción?
2. Rendimiento histórico del equipo
3. Características del enfrentamiento entre razas
4. La aleatoriedad inherente de Blood Bowl

Guías de multiplicadores:
- Resultados simples y probables (favorito gana): 1.5x - 2.5x
- Dificultad moderada (marcadores exactos, sorpresas): 3x - 6x
- Predicciones difíciles/específicas: 7x - 15x
- Resultados muy improbables: 15x - 50x
- Casi imposibles: 50x - 100x

Responde SOLO con JSON válido:
{{
    "multiplier": <número entre {min_mult} y {max_mult}>,
    "confidence": <número entre 0 y 1>,
    "rationale": "<explicación breve EN ESPAÑOL>"
}}""".format(min_mult=AIBet.MIN_MULTIPLIER, max_mult=AIBet.MAX_MULTIPLIER)
        else:
            language_instruction = ""
            task_description = f"""## Task
Estimate a fair payout multiplier for this bet. Consider:
1. How specific/difficult is the prediction?
2. Historical team performance
3. Race matchup characteristics
4. Blood Bowl's inherent randomness

Multiplier guidelines:
- Simple likely outcomes (favorite wins): 1.5x - 2.5x
- Moderate difficulty (exact scores, upsets): 3x - 6x
- Hard/specific predictions: 7x - 15x
- Very unlikely outcomes: 15x - 50x
- Near impossible: 50x - 100x

Respond ONLY with valid JSON:
{{
    "multiplier": <number between {AIBet.MIN_MULTIPLIER} and {AIBet.MAX_MULTIPLIER}>,
    "confidence": <number between 0 and 1>,
    "rationale": "<brief explanation>"
}}"""
        
        prompt = f"""You are an expert Blood Bowl betting analyst. Analyze this custom bet and estimate a fair multiplier.
{language_instruction}

## Match
{home_team.name} ({home_team.race.name}) vs {away_team.name} ({away_team.race.name})

### {home_team.name} Stats:
- Team Value: {home_team.current_tv:,}g
- Record: {home_team.wins}W-{home_team.draws}D-{home_team.losses}L
- TDs For/Against: {home_team.touchdowns_for}/{home_team.touchdowns_against}
- Casualties Inflicted/Suffered: {home_team.casualties_inflicted}/{home_team.casualties_suffered}
- Rerolls: {home_team.rerolls} | Fan Factor: {home_team.fan_factor}

### {away_team.name} Stats:
- Team Value: {away_team.current_tv:,}g
- Record: {away_team.wins}W-{away_team.draws}D-{away_team.losses}L
- TDs For/Against: {away_team.touchdowns_for}/{away_team.touchdowns_against}
- Casualties Inflicted/Suffered: {away_team.casualties_inflicted}/{away_team.casualties_suffered}
- Rerolls: {away_team.rerolls} | Fan Factor: {away_team.fan_factor}

## The Custom Bet
"{bet_description}"

{task_description}"""

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        
        response_text = response.text.strip()
        
        # Extract JSON from response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        result = json.loads(response_text.strip())
        
        multiplier = float(result.get("multiplier", AIBet.DEFAULT_MULTIPLIER))
        multiplier = max(AIBet.MIN_MULTIPLIER, min(AIBet.MAX_MULTIPLIER, multiplier))
        rationale = result.get("rationale", "")
        confidence = float(result.get("confidence", 0.5))
        
        return (multiplier, rationale, confidence)
        
    except Exception as e:
        if lang == 'es':
            return (AIBet.DEFAULT_MULTIPLIER, f"Análisis IA no disponible: {str(e)}", 0.0)
        return (AIBet.DEFAULT_MULTIPLIER, f"AI analysis unavailable: {str(e)}", 0.0)

