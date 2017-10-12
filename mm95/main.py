import numpy as np
import math
import sys
import time

class CirclesMix:
    ret = []
    origimg = None
    img = None
    hall=-1
    wall=-1

    def dbg(self, st):
        # print >> sys.stderr, st
        print(st, file=sys.stderr)
        sys.stderr.flush()
        # pass

    def myprint(self, st):
        # print >> sys.stderr, st
        print(st, file=sys.stderr)

    # negative is better
    def calcScore(self, currimg):
        return np.sum(np.abs(self.origimg - currimg))

    def parseImage(self, pixels):
        packImg = np.array(pixels) #.reshape([self.hall, self.wall])
        imgflat = np.zeros(self.hall * self.wall * 3)
        imgr = packImg >> 16
        imgg = (packImg >> 8) & 0xff
        imgb = packImg & 0xff
        imgflat[0::3] = imgr
        imgflat[1::3] = imgg
        imgflat[2::3] = imgb
        img = np.array(imgflat).reshape([self.hall, self.wall, 3])
        return img

    def isInCircle(self, h, w, ch, cw, radius):
        return ((h - ch) ** 2 + (w - cw) ** 2) <= radius ** 2

    # List of [h,[wmin,wmax]] included in the circle
    def getInCircleList(self, ch, cw, radius):
        rlist = []
        hmin = max(ch - radius, 0)
        hmax = min(ch + radius, self.hall - 1)
        for h in range(hmin, hmax + 1):
            wd = math.sqrt(radius ** 2 - (h - ch) ** 2)
            wmin = max(math.ceil(cw - wd), 0)
            wmax = min(math.floor(cw + wd), self.wall - 1)
            rlist.append([h, [wmin, wmax]])
        return rlist

    def packColor(self, colArr):
        cTrim = (np.minimum(colArr,255))
        return (int(cTrim[0]) << 16) | (int(cTrim[1]) << 8) | int(cTrim[2])

    # Get the best color for the circle, without actually adding it
    def getBestColor(self, currimg, ch, cw, radius):
        rList = self.getInCircleList(ch, cw, radius)
        cavg = np.zeros(3)
        pnum = 0
        for r in rList:
            h = r[0]
            wmin = r[1][0]
            wmax = r[1][1]
            cavg += sum(np.abs(2*self.origimg[h][wmin:(wmax + 1)] - currimg[h][wmin:(wmax + 1)]))
            pnum += wmax-wmin+1
        cavg /= pnum
        # bc = self.packColor(cavg)
        cTrim = (np.minimum(cavg, 255))
        bc = np.floor(cTrim)
        # self.dbg('color = %s' % bc)
        return bc

    # Calculate gain when the circle is added to the current image, without actually adding it
    # negative is better
    def calcGain(self, currimg, ch, cw, radius, rgbval):
        rList = self.getInCircleList(ch, cw, radius)
        origdiff = 0
        newdiff = 0
        for r in rList:
            h = r[0]
            wmin = r[1][0]
            wmax = r[1][1]
            origdiff += np.sum(np.abs(self.origimg[h][wmin:(wmax + 1)] - currimg[h][wmin:(wmax + 1)]))
            newdiff += np.sum(np.abs(
                self.origimg[h][wmin:(wmax + 1)] - np.floor((currimg[h][wmin:(wmax + 1)] + np.tile(rgbval,((wmax + 1)-wmin,1))) / 2)))
        return newdiff - origdiff

    # Add circle to current image and return new image
    def addCircleToImage(self, currimg, ch, cw, radius, rgbval):
        rList = self.getInCircleList(ch, cw, radius)
        newimg = np.copy(currimg)
        for r in rList:
            h = r[0]
            wmin = r[1][0]
            wmax = r[1][1]
            newimg[h][wmin:(wmax + 1)] = np.floor((currimg[h][wmin:(wmax + 1)] + np.tile(rgbval,((wmax + 1)-wmin,1))) / 2)
        return newimg

    def add(self, t):
        CirclesMix.ret = CirclesMix.ret + t


    def drawImage(self, H, pixels, N):
        start = time.time()
        maxtime = 19.0
        itermaxtime = 17.0
        self.hall = H
        self.wall = int(len(pixels)/H)
        self.img = np.zeros([self.hall,self.wall,3])
        self.origimg = self.parseImage(pixels)

        currimg = np.zeros([self.hall,self.wall,3])
        score = self.calcScore(currimg)

        iterstart = time.time()
        itertime = (itermaxtime-(iterstart-start))/N
        lastline = ''

        for iter in range(0,N):
            mingain = 0
            minrad = -1
            minch = -1
            mincw = -1
            minrgb = np.zeros(3)
            doRetry = True
            retry = 0
            while doRetry:
                ch = np.random.randint(self.hall)
                cw = np.random.randint(self.wall)
                # radius = np.random.randint(200*(N-iter)/N+30)
                latestr = ''
                if (iter < N / 2):
                    if(iter==0 and retry==0):
                        radCand = [1000,100]
                    else:
                        radCand = [10,30,60,100,200]
                else:
                    radCand = [10,5,20,40,60,100]

                for radius in radCand:
                    rgbval = self.getBestColor(currimg,ch,cw,radius)
                    gain = self.calcGain(currimg, ch, cw, radius, rgbval)
                    if(iter==0):
                        self.dbg('radius=%4d gain=%8d' % (radius,gain))
                    if(radius==10 and gain>-10000+retry*1000):
                        break
                    if(gain<mingain):
                        mingain = gain
                        minrad = radius
                        minch = ch
                        mincw = cw
                        minrgb = rgbval
                    if (mingain < 0):
                        elapsedtime = time.time() - iterstart
                        latesec = elapsedtime - itertime * (iter+1)
                        if (latesec > 0):
                            latestr = ('Late by %f sec. retry=%d' % (latesec,retry))
                            doRetry = False
                            break
                retry += 1
            if(minrad>=0):
                # self.dbg('%3d: gain=%d, (ch,cw,minrad)=(%d,%d,%d), color=%s ' % (iter,mingain,ch,cw,minrad,minrgb))
                col = self.packColor(minrgb)
                self.add([minch,mincw,minrad, col]);
                currimg = self.addCircleToImage(currimg,minch,mincw,minrad,minrgb)
                score = score + mingain #self.calcScore(currimg)
                lastline = '%3d: score=%9d, gain=%8d, (ch,cw,minrad)=(%3d,%3d,%3d), color=%s %s' % (iter,score,mingain,minch,mincw,minrad,minrgb,latestr)
                self.dbg(lastline)
                if(iter==0):
                    self.myprint(lastline)
            if (time.time() - start > maxtime):
                self.myprint('Time up. Breaking at %d (N=%d)' % (iter,N))
                break

        self.myprint(lastline)

        return CirclesMix.ret


# -------8<------- end of solution submitted to the website -------8<-------

import sys
H = int(input())
S = int(input())
pixels = []
for i in range(S):
    pixels.append(int(input()))
N = int(input())

cm = CirclesMix()
ret = cm.drawImage(H, pixels, N)
print(len(ret))
for num in ret:
    print(num)
sys.stdout.flush()

