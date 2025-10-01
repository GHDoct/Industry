import pygame
import systeme as ss

# self.base_fond contient une copie de la surface sans popup

class gui():

    def __init__(self, systeme, dim = [800, 600]) -> None:
        self.dim = dim
        self.systeme = systeme
        self.init_fond(self.dim)

    def init_fond(self, dim = [800, 600], font_size = 18, proportion_espace = 35):

        pygame.init()
        self.surface = pygame.display.set_mode((dim[0], dim[1]))
        self.surface.fill((255,255,255))        
        proportion_contenu = 100-proportion_espace 
        
        margin_width = int(proportion_espace*dim[0]/100 //(len(self.systeme.cellules)+1))
        cell_width = int(proportion_contenu*dim[0]/100 //len(self.systeme.cellules))
        offset = 5

        self.rectangles = []


        for i in range(len(self.systeme.cellules)):
            x = int(margin_width*(1+i) + cell_width*(i))

            margin_height = int(proportion_espace*dim[1]/100 //(len(self.systeme.cellules[i].ressources)+1))
            ress_height = int(proportion_contenu*dim[1]/100 //len(self.systeme.cellules[i].ressources))

            pt1 = (x-offset, margin_height-offset)
            pt2 = (x+cell_width+offset, dim[1]-margin_height+offset)
            clr = (0,0,0)

            pygame.draw.rect(self.surface, clr, pygame.Rect(pt1[0], pt1[1], pt2[0]-pt1[0], pt2[1]-pt1[1]), 4, 3)

            font = pygame.font.Font(None, font_size)
            text = font.render(f"Cellule '{self.systeme.cellules[i].id}'", True, clr)
            text_rect = text.get_rect(midbottom = ((pt1[0]+pt2[0])/2, margin_height - 5))
            self.surface.blit(text, text_rect)
            self.rectangles.append([])

            for j in range(len(self.systeme.cellules[i].ressources)):
                y = int(margin_height*(j+1) + ress_height*(j))
                pt3 = (x,y)
                pt4 = (x+cell_width, y+ress_height)
            
                rect = pygame.Rect(pt3[0], pt3[1], pt4[0]-pt3[0], pt4[1]-pt3[1])
                pygame.draw.rect(self.surface, clr, rect, 2, 3)
                self.rectangles[i].append(rect)
                
                font = pygame.font.Font(None, font_size)
                text = font.render(f"Ressource '{self.systeme.cellules[i].ressources[j].id}'", True, clr)
                text_rect = text.get_rect(center=((pt3[0]+pt4[0])/2, (pt3[1]+pt4[1])/2))
                self.surface.blit(text, text_rect)
            
            self.base_fond = self.surface.copy()

    def reset_surface(self):
        self.surface.blit(self.base_fond.copy(), (0,0))

    def check_hover_ressource(self):
        for cell in range(len(self.rectangles)):
            for ress in range(len(self.rectangles[cell])):
                rect = self.rectangles[cell][ress]
                if rect.collidepoint(pygame.mouse.get_pos()):
                    return True, cell, ress
        return False, None, None

    def do_clic(self):
        hover, cell, ress = self.check_hover_ressource()
        
        if hover == False :
            self.reset_surface()
        else:
            self.reset_surface()
            popup = self.draw_popup()
            coords = self.rectangles[cell][ress].center
            if cell>=len(self.systeme.cellules)//2:
                coords = (coords[0]-popup.get_width(), coords[1])
            
            if ress>=len(self.systeme.cellules[cell].ressources)//2:
                coords = (coords[0], coords[1]-popup.get_height())

            self.surface.blit(popup, coords)


    def draw_popup(self):
        # displays the Q (ids of items), with the current item running,
        # current state(setup, proccessing, free or panne), estimated cost to finish Q ...
        s = pygame.Surface((120,70))
        s.fill((255,0,0))
        return s

    def run(self):
        run = True
        while run:

            for event in pygame.event.get():

                if event.type == pygame.QUIT or event.type == pygame.KEYDOWN:
                    run =False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.do_clic()

            pygame.display.flip()

        pygame.quit()







