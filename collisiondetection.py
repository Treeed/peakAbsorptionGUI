import math


class CollisionDetection:
    def col_check(self,next_bs,used_bs,target):
        #QtCore.pyqtRemoveInputHook() #for debugging
        #pdb.set_trace() #for debugging
        col_issues = [] #captures colliding beamstops in a list
        vec_target=self.calc_vec_len(next_bs[0],target[0],next_bs[1],target[1]) #is needed later for comparison
        for i in range(0, len(used_bs)):
            next_vec=self.calc_vec_len(used_bs[i][0],next_bs[0],used_bs[i][1],next_bs[1])
            if next_vec < vec_target:
                alpha_target=self.calc_alpha(target[0],next_bs[0],target[1],next_bs[1])
                alpha_next=self.calc_alpha(used_bs[i][0],next_bs[0],used_bs[i][1],next_bs[1])
                alpha_check=alpha_next-alpha_target
                pass_distance=next_vec*math.tan(math.pi/180*alpha_check)
                if abs(pass_distance) < 15:
                    used_bs[i][2]=next_vec
                    col_issues.append(used_bs[i])

        if len(col_issues) > 1:
            col_issues=self.sort_ind(col_issues, 2)
        #pdb.set_trace()
        #if len(col_issues)>0: #this if block was just for testing the bypass function
        #    bypass=self.calc_bypass(next_bs,col_issues,20)
        return col_issues

    def calc_bypass(self,next_bs,col_issues,dist):
        alpha_next=self.calc_alpha(col_issues[0][0],next_bs[0],col_issues[0][1],next_bs[1])
        new_x=dist*math.cos(90-(math.pi/180*alpha_next))+col_issues[0][0]
        new_y=dist*math.sin(90-(math.pi/180*alpha_next))+col_issues[0][1]
        newer_y=dist/math.sin(90-(math.pi/180*alpha_next))+col_issues[0][1]
        return [0.001+col_issues[0][0],newer_y]# will be changed to [col_issues[0][0],newer_y] and newer_y will be renamed

    def find_path(self,target,next_bs,used_bs,dist):#first try
        kascade=[]
        kascade.append(target)
        col_issues=[]
        col_issues=self.col_check(next_bs,used_bs,target)
        if len(col_issues) > 0:
            while len(col_issues) > 0:
                bypass=self.calc_bypass(next_bs,col_issues,dist)
                kascade.append(bypass)
                next_bs=bypass
                col_issues=self.col_check(next_bs,used_bs,target)
        return kascade

    def calc_alpha(self, xn, x0, yn, y0):
        alpha = 180 / math.pi * math.atan(float(yn - y0) / float(xn - x0))
        # alpha=math.atan(3/2)
        return alpha

    def calc_vec_len(self, xn, x0, yn, y0):
        length = math.sqrt(pow((xn - x0), 2) + pow((yn - y0), 2))
        return length

    def sort_ind(self, x, item_ind):
        x = sorted(x, key=lambda item: item[item_ind])
        return x
