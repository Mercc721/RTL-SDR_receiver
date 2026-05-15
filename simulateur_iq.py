import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider

def simulateur_sdr_interactif():
    # --- 1. Paramètres initiaux (en MHz pour simplifier l'affichage) ---
    init_f_rf = 105.0  # MHz
    init_f_lo = 100.0  # MHz

    # Axe du temps (1 microseconde, 2000 points)
    t = np.linspace(0, 1e-6, 2000)
    t_us = t * 1e6  # Pour l'axe X en microsecondes

    # --- 2. Préparation de la fenêtre ---
    plt.style.use('dark_background')
    # On laisse de la place en bas (bottom=0.25) pour mettre les curseurs
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    plt.subplots_adjust(bottom=0.25, hspace=0.4)
    fig.suptitle("Simulateur SDR Interactif", fontsize=16, fontweight='bold')

    # --- 3. Tracé initial des ondes ---
    # On stocke les lignes tracées dans des variables (line_rf, line_i, etc.) 
    # pour pouvoir les modifier plus tard sans redessiner toute la fenêtre.
    
    # Graphe 1: RF
    line_rf, = ax1.plot(t_us, np.cos(2 * np.pi * (init_f_rf*1e6) * t), color='dodgerblue', lw=1.5)
    ax1.set_title("Signal RF Reçu")
    ax1.set_ylim(-1.5, 1.5)
    ax1.grid(True, alpha=0.3)

    # Graphe 2: LO
    line_lo_i, = ax2.plot(t_us, np.cos(2 * np.pi * (init_f_lo*1e6) * t), color='orange', lw=1.5, label='I (Cos)')
    line_lo_q, = ax2.plot(t_us, np.sin(2 * np.pi * (init_f_lo*1e6) * t), color='limegreen', lw=1.5, label='Q (Sin)')
    ax2.set_title("Oscillateur Local (LO)")
    ax2.set_ylim(-1.5, 1.5)
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)

    # Graphe 3: Bande de Base (Soustraction RF - LO)
    f_bb_init = init_f_rf - init_f_lo
    line_bb_i, = ax3.plot(t_us, np.cos(2 * np.pi * (f_bb_init*1e6) * t), color='orange', lw=2, label='Bande de Base I')
    line_bb_q, = ax3.plot(t_us, np.sin(2 * np.pi * (f_bb_init*1e6) * t), color='limegreen', lw=2, linestyle='--', label='Bande de Base Q')
    ax3.set_title(f"Sortie Bande de Base (Différence : {f_bb_init:.1f} MHz)")
    ax3.set_xlabel('Temps (Microsecondes)')
    ax3.set_ylim(-1.5, 1.5)
    ax3.legend(loc='upper right')
    ax3.grid(True, alpha=0.3)

    # --- 4. Création des Curseurs (Sliders) ---
    # Définition des zones à l'écran pour les curseurs [gauche, bas, largeur, hauteur]
    ax_rf = plt.axes([0.15, 0.1, 0.65, 0.03], facecolor='#222222')
    ax_lo = plt.axes([0.15, 0.05, 0.65, 0.03], facecolor='#222222')

    # Création des objets Slider
    slider_rf = Slider(ax_rf, 'Fréq. RF (MHz)', 80.0, 120.0, valinit=init_f_rf, valstep=0.5, color='dodgerblue')
    slider_lo = Slider(ax_lo, 'Fréq. LO (MHz)', 80.0, 120.0, valinit=init_f_lo, valstep=0.5, color='gray')

    # --- 5. La Fonction de Mise à Jour (Le Moteur Interactif) ---
    def update(val):
        # On récupère les nouvelles valeurs des curseurs
        f_rf = slider_rf.val * 1e6
        f_lo = slider_lo.val * 1e6
        f_bb = f_rf - f_lo

        # On recalcule les équations mathématiques
        new_rf = np.cos(2 * np.pi * f_rf * t)
        new_lo_i = np.cos(2 * np.pi * f_lo * t)
        new_lo_q = np.sin(2 * np.pi * f_lo * t)
        new_bb_i = np.cos(2 * np.pi * f_bb * t)
        new_bb_q = np.sin(2 * np.pi * f_bb * t)

        # On injecte les nouvelles données dans les lignes existantes
        line_rf.set_ydata(new_rf)
        line_lo_i.set_ydata(new_lo_i)
        line_lo_q.set_ydata(new_lo_q)
        line_bb_i.set_ydata(new_bb_i)
        line_bb_q.set_ydata(new_bb_q)

        # On met à jour le titre du dernier graphique
        ax3.set_title(f"Sortie Bande de Base (Différence : {f_bb / 1e6:.1f} MHz)")
        
        # On demande à Matplotlib de redessiner l'image
        fig.canvas.draw_idle()

    # On "attache" la fonction update aux mouvements des curseurs
    slider_rf.on_changed(update)
    slider_lo.on_changed(update)

    plt.show()

if __name__ == "__main__":
    simulateur_sdr_interactif()