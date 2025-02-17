import gurobipy as gp
from gurobipy import GRB
import sys
from pathlib import Path

def lire_input(filename):
    """Lit le fichier d'entrée et renvoie les données des photos."""
    photos = []
    with open(filename) as f:
        n = int(f.readline())
        for i in range(n):
            line = f.readline().strip().split()
            orientation = line[0]  # 'H' ou 'V'
            num_tags = int(line[1])
            tags = set(line[2:2+num_tags])
            photos.append((i, orientation, tags))
    return photos

def creer_slides(photos):
    """Crée toutes les slides possibles à partir des photos."""
    slides = []
    
    # Ajout des photos horizontales directement comme slides
    slides.extend(([i], tags) for i, orientation, tags in photos if orientation == 'H')
    
    # Création de toutes les paires possibles de photos verticales
    verticales = [(i, tags) for i, orientation, tags in photos if orientation == 'V']
    for i in range(len(verticales)):
        for j in range(i + 1, len(verticales)):
            # Pour chaque paire de photos verticales, créer une slide
            # avec leurs IDs et l'union de leurs tags
            id1, tags1 = verticales[i]
            id2, tags2 = verticales[j]
            slides.append(([id1, id2], tags1 | tags2))
    
    return slides

def calculer_score(tags1, tags2):
    """Calcule le score entre deux slides."""
    tags_communs = len(tags1.intersection(tags2))
    tags_uniquement_1 = len(tags1.difference(tags2))
    tags_uniquement_2 = len(tags2.difference(tags1))
    return min(tags_communs, tags_uniquement_1, tags_uniquement_2)

def construire_modele(slides):
    """Construit et résout le modèle d'optimisation."""
    model = gp.Model("diaporama")
    
    # Création des variables binaires pour sélectionner les slides
    slide_vars = {}
    for i in range(len(slides)):
        for pos in range(len(slides)):
            slide_vars[i,pos] = model.addVar(vtype=GRB.BINARY, name=f"slide_{i}_pos_{pos}")

    # Chaque position ne peut avoir qu'une seule slide au maximum
    for pos in range(len(slides)):
        model.addConstr(gp.quicksum(slide_vars[i,pos] for i in range(len(slides))) <= 1)
    
    # Chaque slide ne peut être utilisée qu'une seule fois au maximum
    for i in range(len(slides)):
        model.addConstr(gp.quicksum(slide_vars[i,pos] for pos in range(len(slides))) <= 1)
    
    # Chaque photo ne peut être utilisée qu'une seule fois au maximum
    utilisations_photo = {}
    for slide_idx, (photo_ids, _) in enumerate(slides):
        for photo_id in photo_ids:
            if photo_id not in utilisations_photo:
                utilisations_photo[photo_id] = []
            utilisations_photo[photo_id].extend([slide_vars[slide_idx,pos] for pos in range(len(slides))])
            
    for photo_id, utilisations in utilisations_photo.items():
        model.addConstr(gp.quicksum(utilisations) <= 1, name=f"photo_{photo_id}_unique")
    
    # Calcul de l'objectif : somme des scores entre slides consécutives
    obj = 0
    for pos in range(len(slides)-1):
        for i in range(len(slides)):
            for j in range(len(slides)):
                score = calculer_score(slides[i][1], slides[j][1])
                obj += score * slide_vars[i,pos] * slide_vars[j,pos+1]
    
    # Définition de l'objectif pour maximiser l'intérêt total
    model.setObjective(obj, GRB.MAXIMIZE)
    
    # S'assurer qu'il y a au moins une slide
    model.addConstr(gp.quicksum(slide_vars[i,0] for i in range(len(slides))) >= 1)
    
    return model, slide_vars

def get_solution(slide_vars, slides):
    """Extrait la solution à partir des variables du modèle."""
    n = len(slides)
    slides_retenues = []
    
    # Pour chaque position
    for pos in range(n):
        # Chercher quelle slide est à cette position
        for i in range(n):
            if slide_vars[i,pos].X > 0.5:
                slides_retenues.append(i)
                break
        # Si on ne trouve pas de slide à cette position, on arrête
        if len(slides_retenues) != pos + 1:
            break
            
    return slides_retenues

def ecrire_solution(filename, slides_retenues, slides):
    """Écrit la solution dans le fichier de sortie."""
    with open(filename, 'w') as f:
        # Écriture du nombre de slides
        f.write(f"{len(slides_retenues)}\n")
        
        # Écriture de chaque slide
        for slide_idx in slides_retenues:
            photo_ids = slides[slide_idx][0]
            f.write(" ".join(map(str, photo_ids)) + "\n")

def main():
    if len(sys.argv) != 2:
        print("Usage: python slideshow.py <fichier_entrée>")
        sys.exit(1)
    
    fichier_entree = sys.argv[1]
    fichier_sortie = "slideshow.sol"
    
    # Lecture des données
    photos = lire_input(fichier_entree)
    
    # Création des slides potentielles
    slides = creer_slides(photos)
    
    # Construction et résolution du modèle
    model, slide_vars = construire_modele(slides)
    
    # Configuration de Gurobi
    model.Params.TimeLimit = 90  # Limite de temps de 90 secondes
    
    # Optimisation
    model.optimize()
    
    # Récupération de la solution
    slides_retenues = get_solution(slide_vars, slides)
    
    # Écriture de la solution
    ecrire_solution(fichier_sortie, slides_retenues, slides)

if __name__ == "__main__":
    main()