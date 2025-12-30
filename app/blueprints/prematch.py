"""Pre-match activities blueprint."""
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, session, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import (
    Match, Team, StarPlayer,
    MatchInducement, PreMatchSubmission,
    get_available_inducements, calculate_petty_cash, get_inducements_data
)

prematch_bp = Blueprint("prematch", __name__)


def get_locale():
    """Get current locale from session."""
    return session.get('language', 'en')


@prematch_bp.route("/match/<int:match_id>")
@login_required
def index(match_id: int):
    """View pre-match activities overview for a match."""
    match = Match.query.get_or_404(match_id)
    lang = get_locale()
    
    # Check if user is involved in this match
    is_home_coach = current_user.id == match.home_team.coach_id
    is_away_coach = current_user.id == match.away_team.coach_id
    is_commissioner = match.league and current_user.id == match.league.commissioner_id
    
    if not (is_home_coach or is_away_coach or is_commissioner or current_user.is_admin):
        if lang == 'es':
            flash("No tienes permiso para ver esta página.", "danger")
        else:
            flash("You don't have permission to view this page.", "danger")
        return redirect(url_for("matches.view", match_id=match.id))
    
    # Calculate petty cash for both teams
    home_petty_cash, away_petty_cash = calculate_petty_cash(match.home_team, match.away_team)
    
    # Get pre-match submissions
    home_submission = match.get_team_prematch_submission(match.home_team_id)
    away_submission = match.get_team_prematch_submission(match.away_team_id)
    
    # Get inducements for each team
    home_inducements = match.get_team_inducements(match.home_team_id)
    away_inducements = match.get_team_inducements(match.away_team_id)
    
    # Calculate total inducement costs
    home_inducements_cost = sum(ind.total_cost for ind in home_inducements)
    away_inducements_cost = sum(ind.total_cost for ind in away_inducements)
    
    return render_template(
        "prematch/index.html",
        match=match,
        home_petty_cash=home_petty_cash,
        away_petty_cash=away_petty_cash,
        home_submission=home_submission,
        away_submission=away_submission,
        home_inducements=home_inducements,
        away_inducements=away_inducements,
        home_inducements_cost=home_inducements_cost,
        away_inducements_cost=away_inducements_cost,
        is_home_coach=is_home_coach,
        is_away_coach=is_away_coach,
        can_edit_home=is_home_coach or is_commissioner or current_user.is_admin,
        can_edit_away=is_away_coach or is_commissioner or current_user.is_admin
    )


@prematch_bp.route("/match/<int:match_id>/team/<int:team_id>/inducements", methods=["GET", "POST"])
@login_required
def inducements(match_id: int, team_id: int):
    """Manage inducements for a team in a match."""
    match = Match.query.get_or_404(match_id)
    team = Team.query.get_or_404(team_id)
    lang = get_locale()
    
    # Validate team is in the match
    if team_id not in [match.home_team_id, match.away_team_id]:
        abort(404)
    
    # Check permission
    is_coach = current_user.id == team.coach_id
    is_commissioner = match.league and current_user.id == match.league.commissioner_id
    
    if not (is_coach or is_commissioner or current_user.is_admin):
        abort(403)
    
    # Check if match is in a state where inducements can be modified
    if match.status not in ["scheduled", "prematch"]:
        if lang == 'es':
            flash("Los incentivos no se pueden modificar una vez que el partido ha comenzado.", "warning")
        else:
            flash("Inducements cannot be modified once the match has started.", "warning")
        return redirect(url_for("prematch.index", match_id=match.id))
    
    # Get or create pre-match submission
    submission = PreMatchSubmission.query.filter_by(
        match_id=match_id, team_id=team_id
    ).first()
    
    # If inducements already submitted, redirect to view
    if submission and submission.inducements_submitted:
        if lang == 'es':
            flash("Los incentivos ya han sido enviados para este equipo.", "info")
        else:
            flash("Inducements have already been submitted for this team.", "info")
        return redirect(url_for("prematch.index", match_id=match.id))
    
    # Calculate petty cash
    is_home = team_id == match.home_team_id
    home_petty_cash, away_petty_cash = calculate_petty_cash(match.home_team, match.away_team)
    petty_cash = home_petty_cash if is_home else away_petty_cash
    
    # Get available inducements for this team
    available_inducements = get_available_inducements(team, match)
    
    # Get current inducements
    current_inducements = match.get_team_inducements(team_id)
    current_cost = sum(ind.total_cost for ind in current_inducements)
    
    # Calculate remaining budget (petty cash + any treasury the coach wants to use)
    available_budget = petty_cash + team.treasury
    remaining_budget = available_budget - current_cost
    
    # Get star players available to this team's race
    available_stars = StarPlayer.query.filter(
        StarPlayer.available_to_races.any(id=team.race_id)
    ).all()
    
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "add":
            # Add an inducement
            ind_id = request.form.get("inducement_id")
            quantity = int(request.form.get("quantity", 1))
            
            # Find inducement definition
            ind_def = next((i for i in available_inducements if i["id"] == ind_id), None)
            if not ind_def:
                if lang == 'es':
                    flash("Incentivo no válido.", "danger")
                else:
                    flash("Invalid inducement.", "danger")
                return redirect(url_for("prematch.inducements", match_id=match_id, team_id=team_id))
            
            # Check quantity limits
            existing = MatchInducement.query.filter_by(
                match_id=match_id, team_id=team_id, inducement_id=ind_id
            ).first()
            
            existing_qty = existing.quantity if existing else 0
            max_qty = ind_def.get("max_quantity", 1)
            
            if existing_qty + quantity > max_qty:
                if lang == 'es':
                    flash(f"No puedes tener más de {max_qty} de este incentivo.", "warning")
                else:
                    flash(f"You cannot have more than {max_qty} of this inducement.", "warning")
                return redirect(url_for("prematch.inducements", match_id=match_id, team_id=team_id))
            
            # Calculate cost
            cost_per_unit = ind_def.get("cost", 0)
            total_cost = cost_per_unit * quantity
            
            # Check budget
            if current_cost + total_cost > available_budget:
                if lang == 'es':
                    flash("No tienes suficiente oro para este incentivo.", "danger")
                else:
                    flash("You don't have enough gold for this inducement.", "danger")
                return redirect(url_for("prematch.inducements", match_id=match_id, team_id=team_id))
            
            # Add or update inducement
            if existing:
                existing.quantity += quantity
                existing.total_cost += total_cost
            else:
                name = ind_def.get("name_es" if lang == 'es' else "name", ind_def.get("name"))
                new_ind = MatchInducement(
                    match_id=match_id,
                    team_id=team_id,
                    inducement_id=ind_id,
                    inducement_name=name,
                    quantity=quantity,
                    cost_per_unit=cost_per_unit,
                    total_cost=total_cost
                )
                db.session.add(new_ind)
            
            db.session.commit()
            
            if lang == 'es':
                flash("Incentivo añadido.", "success")
            else:
                flash("Inducement added.", "success")
        
        elif action == "add_star":
            # Add a star player
            star_id = request.form.get("star_player_id", type=int)
            star = StarPlayer.query.get(star_id)
            
            if not star:
                if lang == 'es':
                    flash("Jugador Estrella no válido.", "danger")
                else:
                    flash("Invalid Star Player.", "danger")
                return redirect(url_for("prematch.inducements", match_id=match_id, team_id=team_id))
            
            # Check if star player is available to this team's race
            if team.race not in star.available_to_races:
                if lang == 'es':
                    flash("Este Jugador Estrella no está disponible para tu equipo.", "danger")
                else:
                    flash("This Star Player is not available for your team.", "danger")
                return redirect(url_for("prematch.inducements", match_id=match_id, team_id=team_id))
            
            # Check if already hired
            existing_stars = MatchInducement.query.filter_by(
                match_id=match_id, team_id=team_id, inducement_id="star_player"
            ).all()
            
            if len(existing_stars) >= 2:
                if lang == 'es':
                    flash("Solo puedes contratar hasta 2 Jugadores Estrella.", "warning")
                else:
                    flash("You can only hire up to 2 Star Players.", "warning")
                return redirect(url_for("prematch.inducements", match_id=match_id, team_id=team_id))
            
            # Check if this specific star is already hired
            for existing in existing_stars:
                extra = existing.get_extra_data()
                if extra.get("star_player_id") == star_id:
                    if lang == 'es':
                        flash("Este Jugador Estrella ya ha sido contratado.", "warning")
                    else:
                        flash("This Star Player has already been hired.", "warning")
                    return redirect(url_for("prematch.inducements", match_id=match_id, team_id=team_id))
            
            # Check budget
            if current_cost + star.cost > available_budget:
                if lang == 'es':
                    flash("No tienes suficiente oro para este Jugador Estrella.", "danger")
                else:
                    flash("You don't have enough gold for this Star Player.", "danger")
                return redirect(url_for("prematch.inducements", match_id=match_id, team_id=team_id))
            
            # Add star player inducement
            new_ind = MatchInducement(
                match_id=match_id,
                team_id=team_id,
                inducement_id="star_player",
                inducement_name=star.name,
                quantity=1,
                cost_per_unit=star.cost,
                total_cost=star.cost
            )
            new_ind.set_extra_data({"star_player_id": star_id, "star_player_name": star.name})
            db.session.add(new_ind)
            db.session.commit()
            
            if lang == 'es':
                flash(f"Jugador Estrella {star.name} contratado.", "success")
            else:
                flash(f"Star Player {star.name} hired.", "success")
        
        elif action == "remove":
            # Remove an inducement
            ind_entry_id = request.form.get("inducement_entry_id", type=int)
            ind_entry = MatchInducement.query.get(ind_entry_id)
            
            if ind_entry and ind_entry.match_id == match_id and ind_entry.team_id == team_id:
                db.session.delete(ind_entry)
                db.session.commit()
                if lang == 'es':
                    flash("Incentivo eliminado.", "success")
                else:
                    flash("Inducement removed.", "success")
        
        elif action == "submit":
            # Submit inducements
            if not submission:
                submission = PreMatchSubmission(
                    match_id=match_id,
                    team_id=team_id
                )
                db.session.add(submission)
            
            # Calculate total cost and deduct from treasury
            total_spent = sum(ind.total_cost for ind in match.get_team_inducements(team_id))
            treasury_used = max(0, total_spent - petty_cash)
            
            if treasury_used > team.treasury:
                if lang == 'es':
                    flash("Error: No tienes suficiente tesoro para cubrir los incentivos.", "danger")
                else:
                    flash("Error: Not enough treasury to cover inducements.", "danger")
                return redirect(url_for("prematch.inducements", match_id=match_id, team_id=team_id))
            
            # Deduct from team treasury
            team.treasury -= treasury_used
            
            # Mark as submitted
            submission.submit_inducements()
            submission.total_inducements_cost = total_spent
            
            # Update match pre-match status
            if is_home:
                match.home_prematch_ready = True
            else:
                match.away_prematch_ready = True
            
            # If both teams ready, update match status
            if match.home_prematch_ready and match.away_prematch_ready:
                match.status = "prematch"
            
            db.session.commit()
            
            if lang == 'es':
                flash("¡Incentivos enviados! Tu equipo está listo para el partido.", "success")
            else:
                flash("Inducements submitted! Your team is ready for the match.", "success")
            
            return redirect(url_for("prematch.index", match_id=match.id))
        
        return redirect(url_for("prematch.inducements", match_id=match_id, team_id=team_id))
    
    # Refresh current data
    current_inducements = match.get_team_inducements(team_id)
    current_cost = sum(ind.total_cost for ind in current_inducements)
    
    return render_template(
        "prematch/inducements.html",
        match=match,
        team=team,
        available_inducements=available_inducements,
        current_inducements=current_inducements,
        current_cost=current_cost,
        petty_cash=petty_cash,
        available_budget=available_budget,
        remaining_budget=available_budget - current_cost,
        available_stars=available_stars,
        is_home=is_home
    )


@prematch_bp.route("/match/<int:match_id>/team/<int:team_id>/skip", methods=["POST"])
@login_required
def skip_inducements(match_id: int, team_id: int):
    """Skip inducements for a team (submit with no inducements)."""
    match = Match.query.get_or_404(match_id)
    team = Team.query.get_or_404(team_id)
    lang = get_locale()
    
    # Validate team is in the match
    if team_id not in [match.home_team_id, match.away_team_id]:
        abort(404)
    
    # Check permission
    is_coach = current_user.id == team.coach_id
    is_commissioner = match.league and current_user.id == match.league.commissioner_id
    
    if not (is_coach or is_commissioner or current_user.is_admin):
        abort(403)
    
    # Check if match is in a state where this is allowed
    if match.status not in ["scheduled", "prematch"]:
        if lang == 'es':
            flash("No se puede modificar el estado pre-partido.", "warning")
        else:
            flash("Cannot modify pre-match state.", "warning")
        return redirect(url_for("matches.view", match_id=match.id))
    
    # Get or create submission
    submission = PreMatchSubmission.query.filter_by(
        match_id=match_id, team_id=team_id
    ).first()
    
    if submission and submission.inducements_submitted:
        if lang == 'es':
            flash("Los incentivos ya han sido enviados.", "info")
        else:
            flash("Inducements have already been submitted.", "info")
        return redirect(url_for("prematch.index", match_id=match.id))
    
    if not submission:
        submission = PreMatchSubmission(
            match_id=match_id,
            team_id=team_id
        )
        db.session.add(submission)
    
    submission.submit_inducements()
    submission.total_inducements_cost = 0
    
    # Update match pre-match status
    is_home = team_id == match.home_team_id
    if is_home:
        match.home_prematch_ready = True
    else:
        match.away_prematch_ready = True
    
    # If both teams ready, update match status
    if match.home_prematch_ready and match.away_prematch_ready:
        match.status = "prematch"
    
    db.session.commit()
    
    if lang == 'es':
        flash("Actividades pre-partido saltadas. Tu equipo está listo.", "success")
    else:
        flash("Pre-match activities skipped. Your team is ready.", "success")
    
    return redirect(url_for("prematch.index", match_id=match.id))


@prematch_bp.route("/api/match/<int:match_id>/inducements")
@login_required
def api_inducements(match_id: int):
    """API endpoint to get inducements data for a match."""
    match = Match.query.get_or_404(match_id)
    
    # Authorization: Only involved coaches, commissioner, or admin can access
    is_home_coach = current_user.id == match.home_team.coach_id
    is_away_coach = current_user.id == match.away_team.coach_id
    is_commissioner = match.league and current_user.id == match.league.commissioner_id
    
    if not (is_home_coach or is_away_coach or is_commissioner or current_user.is_admin):
        return jsonify({"error": "Unauthorized"}), 403
    
    home_petty_cash, away_petty_cash = calculate_petty_cash(match.home_team, match.away_team)
    
    home_inducements = [{
        "id": ind.id,
        "inducement_id": ind.inducement_id,
        "name": ind.inducement_name,
        "quantity": ind.quantity,
        "cost_per_unit": ind.cost_per_unit,
        "total_cost": ind.total_cost
    } for ind in match.get_team_inducements(match.home_team_id)]
    
    away_inducements = [{
        "id": ind.id,
        "inducement_id": ind.inducement_id,
        "name": ind.inducement_name,
        "quantity": ind.quantity,
        "cost_per_unit": ind.cost_per_unit,
        "total_cost": ind.total_cost
    } for ind in match.get_team_inducements(match.away_team_id)]
    
    return jsonify({
        "home_team": {
            "id": match.home_team_id,
            "name": match.home_team.name,
            "tv": match.home_team.current_tv,
            "petty_cash": home_petty_cash,
            "inducements": home_inducements,
            "total_cost": sum(i["total_cost"] for i in home_inducements),
            "ready": match.home_prematch_ready
        },
        "away_team": {
            "id": match.away_team_id,
            "name": match.away_team.name,
            "tv": match.away_team.current_tv,
            "petty_cash": away_petty_cash,
            "inducements": away_inducements,
            "total_cost": sum(i["total_cost"] for i in away_inducements),
            "ready": match.away_prematch_ready
        }
    })

