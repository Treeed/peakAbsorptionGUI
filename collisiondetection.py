import math


class CollisionDetection:
    def col_check(self,next_bs,used_bs,target): #next_bs is the startposition of the next unset bs, bs_used contains all bs on the field, target is the next desired position
        #QtCore.pyqtRemoveInputHook() #for debugging
        #pdb.set_trace() #for debugging
        col_issues = [] #captures colliding beamstops in a list
        vec_target=self.calc_vec_len(next_bs[0],target[0],next_bs[1],target[1]) #determine the distance between next_bs and target
        for i in range(0, len(used_bs)): #
            next_vec=self.calc_vec_len(used_bs[i][0],next_bs[0],used_bs[i][1],next_bs[1]) #determine the distance between next_bs and all set bs
            if next_vec < (vec_target+25): #filter: if shorter then vec_target it is not relevant
                alpha_target=self.calc_alpha(target[0],next_bs[0],target[1],next_bs[1]) #calculates angle of horizontal base line of next_bs regarding target position
                alpha_next=self.calc_alpha(used_bs[i][0],next_bs[0],used_bs[i][1],next_bs[1]) #calculates angle of horizontal base line of next_bs regarding used_bs
                alpha_check=alpha_next-alpha_target #calculate relativ angle betwenn alpha_target and alpha_next
                pass_distance=next_vec*math.tan(math.pi/180*alpha_check) #now we can calculate the distance
                #print "pass distance ", pass_distance
                if abs(pass_distance) < 15: #now we can check for issues
                    used_bs[i][2]=next_vec #put the issues in a list
                    col_issues.append(used_bs[i])
                    #print "col_issues", col_issues

        if len(col_issues) > 1:
            col_issues=self.sort_ind(col_issues, 2) #sort the list
        #pdb.set_trace()
        #if len(col_issues)>0: #this if block was just for testing the bypass function
        #    bypass=self.calc_bypass(next_bs,col_issues,20)
        return col_issues

    def calc_bypass(self,next_bs,col_issues,used_bs,dist):
        test=[]
        alpha_next=self.calc_alpha(col_issues[0][0],next_bs[0],col_issues[0][1],next_bs[1])
        new_x=dist*math.cos(90-(math.pi/180*alpha_next))+col_issues[0][0]
        new_y=dist*math.sin(90-(math.pi/180*alpha_next))+col_issues[0][1]
        test=self.col_check(next_bs,used_bs,[new_x,new_y])
        #print len(test)
        if len(test)>0:
            new_x=2*dist*math.cos(90-(math.pi/180*alpha_next))+col_issues[0][0]
            new_y=2*dist*math.sin(90-(math.pi/180*alpha_next))+col_issues[0][1]

        newer_y=dist/math.sin(90-(math.pi/180*alpha_next))+col_issues[0][1]
        #return [0.001+col_issues[0][0],newer_y]# will be changed to [col_issues[0][0],newer_y] and newer_y will be renamed
        return [new_x,new_y]

    def calc_bypass_new(self,next_bs,col_issues,used_bs,target,dist):
        i=0
        j=0
        alpha_target=self.calc_alpha(target[0],next_bs[0],target[1],next_bs[1])  # this calculates the angle towards the x-axis of the vector from next_bs to target
        #print "alpha Target ",alpha_target
        new_x=(-1)*(dist*math.cos(math.pi/180*alpha_target))+col_issues[0][0]  # this calculates a point which is dist away from target and in the direction of the vector from next_bs to target. sometimes x is inverted
        new_y=(dist*math.sin(math.pi/180*alpha_target))+col_issues[0][1]
        test=self.col_check(next_bs,used_bs,[new_x,new_y])
        if len(test)>0:
            while len(test)>0:
                i+=1
                if i <5:
                    #print i
                    new_x=(-1)*(i*dist*math.cos(math.pi/180*alpha_target))+col_issues[0][0]
                    new_y=(i*dist*math.sin(math.pi/180*alpha_target))+col_issues[0][1]
                    test=self.col_check(next_bs,used_bs,[new_x,new_y])
                if i>=5:
                    j+=1
                    new_x=(j*dist*math.cos(math.pi/180*alpha_target))+col_issues[0][0]
                    new_y=(-1)*(j*dist*math.sin(math.pi/180*alpha_target))+col_issues[0][1]
                    test=self.col_check(next_bs,used_bs,[new_x,new_y])
                #print new_x," ",new_y
        return [new_x,new_y]


    def calc_bypass_new_new(self,next_bs,col_issues,used_bs,target,dist,max_multi):
        alpha_target=self.calc_alpha(target[0],next_bs[0],target[1],next_bs[1])  # this calculates the angle towards the x-axis of the vector from next_bs to target
        for dist_multi in range(1, max_multi):  # increasing distance to thing to circumvent in steps of dist
            for angle in [-90, 90]:
                new_x=(dist_multi*dist*math.cos(math.pi/180*(alpha_target+angle)))+col_issues[0][0]  # calculating vector angled off 90° from next_bs to obstacle vector and basing it on obstacle
                new_y=(dist_multi*dist*math.sin(math.pi/180*(alpha_target+angle)))+col_issues[0][1]
                if not self.col_check(next_bs,used_bs,[new_x,new_y]):
                    return [new_x, new_y]
        raise Exception("max multi didn't find a bypass")


    def find_path(self,target,next_bs,used_bs,dist, max_multi):#first try
        #QtCore.pyqtRemoveInputHook() #for debugging
        #pdb.set_trace() #for debugging
        kascade=[]
        col_issues=[]
        col_issues=self.col_check(next_bs,used_bs,target)
        if len(col_issues) > 0:
            while len(col_issues) > 0:
                bypass=self.calc_bypass_new_new(next_bs,col_issues,used_bs,target,dist, max_multi)

                kascade.append(bypass)
                next_bs=bypass
                col_issues=self.col_check(next_bs,used_bs,target)
        #print kascade,"kascade done"
        kascade.append(target)
        return kascade

    def calc_alpha(self, xn, x0, yn, y0):
        if xn - x0 == 0:
            if yn - y0 > 0:
                return 90  # don't divide by zero
            if yn - y0 < 0:
                return -90
            else:
                raise ArithmeticError("both points are the same, don't have an angle")
        alpha = 180 / math.pi * math.atan(float(yn - y0) / float(xn - x0))
        # alpha=math.atan(3/2)
        #print xn,x0
        return alpha

    def calc_vec_len(self, xn, x0, yn, y0):
        length = math.sqrt(pow((xn - x0), 2) + pow((yn - y0), 2))
        return length

    def sort_ind(self, x, item_ind):
        x = sorted(x, key=lambda item: item[item_ind])
        return x
