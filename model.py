import tkinter as tk
from tkinter import messagebox
import numpy as np
import math

# ------------------------
# CONFIGURATION / GLOBALS
# ------------------------

# Logistic calibration anchors (re-anchored: Score=20→0.64%, Score=60→10%)
p1, s1 = 0.0064, 20
p2, s2 = 0.10,   60
L1 = math.log(p1 / (1 - p1))
L2 = math.log(p2 / (1 - p2))
a  = (L2 - L1) / (s2 - s1)
b  = s1 - L1 / a

P_FLOOR    = 0.02    # never below 2%
MAX_FAIR   = 50.0    # cap raw fair odds at 50×
SB_SCALE   = 0.35    # shots-behind penalty scale
BLEND_MODEL = 0.6    # weight on heuristic model when blending with sim
TOTAL_HOLES = 72     # total holes in tournament

# ------------------------
# SIMULATION FUNCTION
# ------------------------

def simulate_win_prob(shots_behind: float,
                      holes_left: int,
                      sg_expect_round: float,
                      contenders: int = 20,
                      sims: int = 5000,
                      rnd_sd: float = 2.4):
    """
    Monte Carlo simulate your chance to win given:
      - shots_behind: strokes you trail the leader
      - holes_left: holes remaining in event
      - sg_expect_round: your expected strokes-gained for remaining holes
      - contenders: size of live contender set
      - rnd_sd: round-to-round score stdev
    """
    mean_delta = -(sg_expect_round * holes_left / 18.0)
    sd_scale   = rnd_sd * math.sqrt(holes_left / 18.0)
    wins = 0
    for _ in range(sims):
        you    = shots_behind + np.random.normal(mean_delta, sd_scale)
        others = np.random.normal(0, sd_scale, size=contenders-1)
        if you <= others.min():
            wins += 1
    return wins / sims

# ------------------------
# CALCULATION LOGIC
# ------------------------

def calculate_score():
    try:
        # --- historic / pre-event metrics ---
        name            = name_entry.get().strip()
        xwins           = float(xwins_entry.get())
        total_shots     = float(total_shots_entry.get())
        putt            = float(putt_entry.get())
        T2G             = float(t2g_entry.get())
        sg_true         = float(sg_true_entry.get())
        sg_expected_pre = float(sg_expected_entry.get())
        course_fit      = float(course_fit_entry.get())
        ranking         = float(ranking_entry.get())
        live_odds       = float(live_odds_entry.get())
        leaderboard_pos = float(leaderboard_pos_entry.get())
        finishes        = [float(e.get()) for e in finish_entries]
        # --- in-play SG metrics ---
        sg_off_tee      = float(sg_off_tee_entry.get())
        sg_approach     = float(sg_approach_entry.get())
        sg_putting      = float(sg_putting_entry.get())
        scrambling      = float(scrambling_entry.get())
        # --- new manual inputs ---
        holes_left      = int(holes_left_entry.get())
        n_contenders    = int(n_contenders_entry.get())
        quality_key     = quality_var.get()
        shots_behind    = float(shots_behind_entry.get())
    except ValueError:
        messagebox.showerror("Input Error", "Please enter valid numbers in every field.")
        return

    # Derived pre-event
    sg_diff   = sg_true - sg_expected_pre
    avg_last5 = sum(finishes) / len(finishes)
    pressure  = sg_diff * 15

    # Build the heuristic score
    score = (
        50
        + xwins
        + total_shots * 0.5
        + putt * 0.5
        + T2G * 0.5
        + pressure
        + course_fit * 20
        - ranking * 0.5
        - leaderboard_pos * 0.3
        - avg_last5 * 0.5
        + sg_off_tee  * 0.5
        + sg_approach * 0.5
        + sg_putting  * 0.5
        - (100 - scrambling) * 0.2
    )

    # Shots-Behind Penalty
    sb_penalty = (shots_behind / math.sqrt(max(holes_left, 1))) * SB_SCALE
    score -= sb_penalty

    # Field quality factor
    field_quality = {"weak": 0.9, "average": 1.0, "strong": 1.1}[quality_key]
    score /= field_quality

    # Clip and logistic mapping → p_model
    score = float(np.clip(score, 0, 100))
    p_model = 1.0 / (1.0 + math.exp(-a * (score - b)))
    p_model = max(p_model, P_FLOOR)

    # --- LIVE SG PROJECTION for remaining holes ---
    holes_played = TOTAL_HOLES - holes_left
    if holes_played > 0:
        sg_so_far = sg_off_tee + sg_approach + sg_putting
        sg_rate_per_hole = sg_so_far / holes_played
        # blend with pre-event if desired
        sg_remaining = 0.5 * sg_expected_pre + 0.5 * (sg_rate_per_hole * holes_left)
    else:
        sg_remaining = sg_expected_pre

    # Monte Carlo simulation with live SG
    p_sim = simulate_win_prob(
        shots_behind=shots_behind,
        holes_left=holes_left,
        sg_expect_round=sg_remaining,
        contenders=n_contenders
    )

    # Blend heuristic + simulation
    p_final = BLEND_MODEL * p_model + (1 - BLEND_MODEL) * p_sim

    # Market and EV
    p_implied = 1.0 / live_odds
    edge      = p_final - p_implied
    fair_model = min(1.0 / p_final, MAX_FAIR)
    fair_blend = 0.7 * fair_model + 0.3 * live_odds
    ev_back = p_final * (live_odds - 1) - (1 - p_final)

    # Output
    out = (
        f"{name}  |  Score: {score:6.2f}%  "
        f"Model: {p_final*100:6.2f}%  Market: {p_implied*100:6.2f}%  "
        f"Edge: {edge*100:+5.2f}%  FairOdds: {fair_blend:5.2f}  "
        f"LiveOdds: {live_odds:4.2f}  EV: {ev_back:+.3f}"
    )
    print(out)
    result_label.config(text=out)

# ------------------------
# BUILD THE GUI
# ------------------------

root = tk.Tk()
root.title("Odds Apex - Golf Model")

# Basic pre-event fields
fields = [
    "Golfer Name", "Expected Wins (xwins)", "Total Shots Gained",
    "Putt", "T2G", "SG True", "SG Expected",
    "Course Fit", "Current Ranking", "Live Odds",
    "Leaderboard Position", "Shots Behind Leader"
]
entries = {}
for i, lbl in enumerate(fields):
    tk.Label(root, text=lbl).grid(row=i, column=0, sticky="e", padx=4, pady=2)
    e = tk.Entry(root)
    e.grid(row=i, column=1, padx=4, pady=2)
    entries[lbl] = e

(
    name_entry, xwins_entry, total_shots_entry, putt_entry,
    t2g_entry, sg_true_entry, sg_expected_entry,
    course_fit_entry, ranking_entry, live_odds_entry,
    leaderboard_pos_entry, shots_behind_entry
) = [entries[l] for l in fields]

# Last 5 finishes
last5_row = len(fields)
tk.Label(root, text="Last 5 Finishes").grid(row=last5_row, column=0, sticky="e", padx=4, pady=2)
finish_frame = tk.Frame(root)
finish_frame.grid(row=last5_row, column=1, pady=2)
finish_entries = []
for j in range(5):
    e = tk.Entry(finish_frame, width=4)
    e.grid(row=0, column=j, padx=2)
    finish_entries.append(e)

# In-play SG stats
sg_stats = ["SG Off Tee", "SG Approach", "SG Putting", "Scrambling %"]
for k, lbl in enumerate(sg_stats, start=last5_row+1):
    tk.Label(root, text=lbl).grid(row=k, column=0, sticky="e", padx=4, pady=2)
    e = tk.Entry(root)
    e.grid(row=k, column=1, padx=4, pady=2)
    if lbl == "SG Off Tee":    sg_off_tee_entry = e
    if lbl == "SG Approach":   sg_approach_entry = e
    if lbl == "SG Putting":    sg_putting_entry = e
    if lbl == "Scrambling %":  scrambling_entry = e

# New round-level inputs
new_row = last5_row + 1 + len(sg_stats)
tk.Label(root, text="Holes Remaining").grid(row=new_row, column=0, sticky="e", padx=4, pady=2)
holes_left_entry = tk.Entry(root)
holes_left_entry.grid(row=new_row, column=1, padx=4, pady=2)

tk.Label(root, text="Contenders").grid(row=new_row+1, column=0, sticky="e", padx=4, pady=2)
n_contenders_entry = tk.Entry(root)
n_contenders_entry.grid(row=new_row+1, column=1, padx=4, pady=2)

tk.Label(root, text="Field Quality").grid(row=new_row+2, column=0, sticky="e", padx=4, pady=2)
quality_var = tk.StringVar(root)
quality_var.set("average")
tk.OptionMenu(root, quality_var, "weak", "average", "strong").grid(row=new_row+2, column=1, padx=4, pady=2)

# Calculate button & result
bottom = new_row + 3
tk.Button(root, text="Calculate Score & EV", command=calculate_score)\
    .grid(row=bottom, column=0, columnspan=2, pady=10)

result_label = tk.Label(root, text="", font=("Helvetica", 10, "bold"),
                        anchor="w", justify="left")
result_label.grid(row=bottom+1, column=0, columnspan=2, sticky="we", pady=4)

root.mainloop()
