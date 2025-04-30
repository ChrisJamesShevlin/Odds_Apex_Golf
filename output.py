import tkinter as tk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
import re

def calculate_lays():
    output_txt.delete("1.0", tk.END)
    lines = input_txt.get("1.0", tk.END).strip().splitlines()

    # read & validate inputs
    try:
        bank = float(balance_entry.get())
        flat_pct = float(flat_pct_entry.get()) / 100.0
        kelly_frac = float(kelly_frac_entry.get()) / 100.0
        if bank <= 0 or flat_pct < 0 or kelly_frac < 0:
            raise ValueError
    except ValueError:
        messagebox.showerror(
            "Input Error",
            "Please enter positive numbers for balance, flat % and Kelly %."
        )
        return

    cap_liability = 0.10 * bank  # per-golfer cap
    candidates = []

    # parse each pasted line
    for line in lines:
        if "|" not in line:
            continue
        name, rest = line.split("|", 1)
        name = name.strip()
        rest = rest.strip()

        # extract Model (12.34%) and LiveOdds (e.g. 5.50)
        m_mod = re.search(r"Model[:%]?\s*([0-9]+(?:\.[0-9]+)?)%", rest)
        m_od  = re.search(r"LiveOdds[:]?[\s]*([0-9]+(?:\.[0-9]+)?)", rest)
        if not (m_mod and m_od):
            continue

        p_model   = float(m_mod.group(1)) / 100.0
        live_odds = float(m_od.group(1))
        if live_odds <= 1:
            continue

        # compute lay EV
        ev_back = p_model * (live_odds - 1) - (1 - p_model)
        ev_lay  = -ev_back
        if ev_lay <= 0:
            continue

        # FLAT-percent stake
        liability_flat = flat_pct * bank
        stake_flat     = liability_flat / (live_odds - 1)

        # MINI-KELLY on positive-edge lays
        f_full      = ev_lay / (live_odds - 1)
        f_mini      = max(0, f_full) * kelly_frac
        stake_kelly = f_mini * bank

        # total stake and liability
        stake     = stake_flat + stake_kelly
        liability = stake * (live_odds - 1)

        # enforce per-golfer cap
        if liability > cap_liability:
            liability = cap_liability
            stake     = liability / (live_odds - 1)

        candidates.append({
            "name":      name,
            "odds":      live_odds,
            "ev_lay":    ev_lay,
            "stake":     stake,
            "liability": liability
        })

    # sort by descending EV
    candidates.sort(key=lambda c: c["ev_lay"], reverse=True)

    # output header
    output_txt.insert(tk.END, f"Bankroll: £{bank:.2f}\n")
    output_txt.insert(tk.END, f"Flat stake %: {flat_pct*100:.2f}% of bank\n")
    output_txt.insert(tk.END, f"Kelly fraction: {kelly_frac*100:.2f}% of full Kelly\n")
    output_txt.insert(tk.END, f"Max liability per golfer (10%): £{cap_liability:.2f}\n\n")

    if not candidates:
        output_txt.insert(tk.END, "No positive-EV lays found.\n")
    else:
        output_txt.insert(tk.END, "Recommendations (flat + mini-Kelly, per-golfer cap):\n")
        output_txt.insert(tk.END, "-----------------------------------------------------------\n")
        for c in candidates:
            output_txt.insert(
                tk.END,
                f"{c['name']:<12} | Odds: {c['odds']:>5.2f} | "
                f"LayEV: {c['ev_lay']:+.3f} | "
                f"Stake: £{c['stake']:>6.2f} | "
                f"Liab: £{c['liability']:>6.2f}\n"
            )
        output_txt.insert(tk.END, "-----------------------------------------------------------\n")

# Build GUI
root = tk.Tk()
root.title("Odds Apex - Lay Optimizer")

tk.Label(root, text="Paste your model output here:")\
    .grid(row=0, column=0, sticky="w", padx=4, pady=4)
input_txt = ScrolledText(root, width=80, height=8)
input_txt.grid(row=1, column=0, columnspan=2, padx=4)

tk.Label(root, text="Account balance (£):")\
    .grid(row=2, column=0, sticky="w", padx=4, pady=(10,2))
balance_entry = tk.Entry(root)
balance_entry.grid(row=2, column=1, sticky="w", padx=4)

tk.Label(root, text="Flat % of Bank per Lay:")\
    .grid(row=3, column=0, sticky="w", padx=4, pady=2)
flat_pct_entry = tk.Entry(root)
flat_pct_entry.insert(0, "1.0")
flat_pct_entry.grid(row=3, column=1, sticky="w", padx=4)

tk.Label(root, text="Kelly % of Full Kelly:")\
    .grid(row=4, column=0, sticky="w", padx=4, pady=2)
kelly_frac_entry = tk.Entry(root)
kelly_frac_entry.insert(0, "25.0")
kelly_frac_entry.grid(row=4, column=1, sticky="w", padx=4)

tk.Button(root, text="Calculate Lays", command=calculate_lays)\
    .grid(row=5, column=0, columnspan=2, pady=8)

tk.Label(root, text="Recommendations:")\
    .grid(row=6, column=0, sticky="w", padx=4, pady=(10,2))
output_txt = ScrolledText(root, width=80, height=12)
output_txt.grid(row=7, column=0, columnspan=2, padx=4, pady=(0,8))

root.mainloop()
