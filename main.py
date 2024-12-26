import pytesseract
import cv2
import subprocess
import numpy as np
import os
import math
import time
import color
import threading
import sys
from yaspin import yaspin


def banner() -> None:
    banner = '''
  #####                                     
 #     # #    # #####   ####  #    # #    # 
 #       #    # #    # #    # #   #  #    # 
  #####  #    # #    # #    # ####   #    # 
       # #    # #    # #    # #  #   #    # 
 #     # #    # #    # #    # #   #  #    # 
  #####   ####  #####   ####  #    #  ####  
                                            
  #####                                     
 #     #  ####  #      #    # ###### #####  
 #       #    # #      #    # #      #    # 
  #####  #    # #      #    # #####  #    # 
       # #    # #      #    # #      #####  
 #     # #    # #       #  #  #      #   #  
  #####   ####  ######   ##   ###### #    # 
                                            
    '''

    print(banner)
    print()
                                            


def tap(x, y) -> None:
    subprocess.run(f"adb shell input tap {x} {y}", shell=True)
    time.sleep(0.01)


def matchTemplate(image: cv2.typing.MatLike, template_path: str, threshold=0.8):
	img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) 
	  
	template = cv2.imread(template_path, 0) 
	  
	w, h = template.shape[::-1] 
	  
	res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED) 
	  
	loc = np.where(res >= threshold) 

	for pt in zip(*loc[::-1]): 
	    cv2.rectangle(image, pt, (pt[0] + w, pt[1] + h), (0, 0, 255), 2) 

	if str(loc) != "(array([], dtype=int64), array([], dtype=int64))":
		centerX = int(((pt[0] + w) + pt[0]) / 2)
		centerY = int(((pt[1] + h) + pt[1]) / 2)
		return centerX, centerY
	else:
		return None, None


def screenshot() -> cv2.typing.MatLike:
    try:
        pipe = subprocess.Popen("adb shell screencap -p", stdin=subprocess.PIPE ,stdout=subprocess.PIPE, shell=True)
        image_bytes = pipe.stdout.read().replace(b'\r\n', b'\n')
        image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    except:
        return None
    return image


def screenshotRegion(x, y, width, height) -> cv2.typing.MatLike:
    image = screenshot()
    cropped_image = image[y:y+height, x:x+width]
    return cropped_image


def printSudoku(sudokuPuzzle: list) -> None:
    print('\n'.join(['\t'.join([str(cell) for cell in row]) for row in sudokuPuzzle]))

def detectDigit(image) -> str:
    image = image[10:100, 10:100]
    image = cv2.resize(image, (0, 0), fx = 0.3, fy = 0.3)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    image = cv2.GaussianBlur(image, (5, 5), 0)
    ret, image = cv2.threshold(image, 150, 255, cv2.THRESH_BINARY)
    # cv2.imshow("", image)
    # cv2.waitKey(0)
    digit = pytesseract.image_to_string(image, config='--oem 3 --psm 10 -c tessedit_char_whitelist=123456789')
    try:
        return int(digit)
    except:
        return 0


def detectGrid():
    image = screenshot()

    gray = cv2.cvtColor(image ,cv2.COLOR_BGR2GRAY)

    kernelSize = 5
    blurGray = cv2.GaussianBlur(gray, (kernelSize, kernelSize), 0)

    lowThreshold = 0
    highThreshold = 200
    edges = cv2.Canny(blurGray, lowThreshold, highThreshold)

    rho = 1  # distance resolution in pixels of the Hough grid
    theta = np.pi / 180  # angular resolution in radians of the Hough grid
    threshold = 15  # minimum number of votes (intersections in Hough grid cell)
    min_line_length = 200  # minimum number of pixels making up a line
    max_line_gap = 20  # maximum gap in pixels between connectable line segments
    line_image = np.copy(image) * 0  # creating a blank to draw lines on

    # Run Hough on edge detected image
    # Output "lines" is an array containing endpoints of detected line segments
    lines = cv2.HoughLinesP(edges, rho, theta, threshold, np.array([]),
                        min_line_length, max_line_gap)

    imageHeight, imageWidth, imageChannels = image.shape
    topLeft = (imageWidth, imageHeight)
    width = 0

    for line in lines:
        for x1,y1,x2,y2 in line:
            if x1 <= topLeft[0] and y1 <= topLeft[1]:
                topLeft = (x1, y1)
                width = math.dist([x1,y1],[x2,y2])
            if x2 <= topLeft[0] and y2 <= topLeft[1]:
                topLeft = (x2, y2)
                width = math.dist([x2,y2],[x1,y1])

    return int(topLeft[0]), int(topLeft[1]), int(width / 9), int(width / 9)



def generateEmptySudoku() -> list:
    sudokuPuzzle = []

    for i in range(9):
        sudokuPuzzle.append([])
        for j in range(9):
            sudokuPuzzle[i].append("-")

    return sudokuPuzzle


def readSudokuFromDeivce() -> list:
    sudokuPuzzle = generateEmptySudoku()
    gridX, gridY, gridUnitWidth, gridUnitHeight = detectGrid()


    for i, row in enumerate(sudokuPuzzle):
        for j, slot in enumerate(row):
            slotImage = screenshotRegion(gridX + j * gridUnitWidth, gridY + i * gridUnitHeight, gridUnitWidth, gridUnitHeight)
            digit = detectDigit(slotImage)
            sudokuPuzzle[i][j] = digit
            
            
    return sudokuPuzzle


def findEmptyLocation(sudokuPuzzle: list, l: list) -> bool:
    for row in range(9):
        for column in range(9):
            if (sudokuPuzzle[row][column] == 0):
                l[0] = row
                l[1] = column
                return True
    return False


def usedInRow(sudokuPuzzle: list, row: int, digit: int) -> bool:
    for i in range(9):
        if(sudokuPuzzle[row][i] == digit):
            return True
    return False


def usedInColumn(sudokuPuzzle: list, column: int, digit: int) -> bool:
    for i in range(9):
        if(sudokuPuzzle[i][column] == digit):
            return True
    return False


def usedInBox(sudokuPuzzle: list, row: int, column: int, digit: int) -> bool:
    for i in range(3):
        for j in range(3):
            if (sudokuPuzzle[row + i][column + j] == digit):
                return True
    return False


def locationIsSafe(sudokuPuzzle: list, row: int, column: int, digit: int) -> bool:
    return (not usedInBox(sudokuPuzzle, row - row % 3, column - column % 3, digit) and
            (not usedInColumn(sudokuPuzzle, column, digit) and
             (not usedInRow(sudokuPuzzle, row, digit))))


def solveSudoku(sudokuPuzzle: list) -> bool:
    
    l = [0, 0]

    if (not findEmptyLocation(sudokuPuzzle, l)):
        return True

    row = l[0]
    column = l[1]

    for digit in range(1, 10):
        if (locationIsSafe(sudokuPuzzle, row, column, digit)):
            sudokuPuzzle[row][column] = digit
            if (solveSudoku(sudokuPuzzle)):
                return True
            
            sudokuPuzzle[row][column] = 0
    return False


def findNumberLocations() -> dict:
    try:
        numberLocationDict = {}
        for i in range(1, 10):
            x, y = matchTemplate(screenshot(), f"Images/Digits/{i}.png")
            numberLocationDict[i] = (x, y)
        return numberLocationDict
    except:
        return None


def inputPuzzle(sudokuPuzzle: list, unsolvedSudokuPuzzle: list, numberLocationDict: dict) -> bool:
    try:
        gridX, gridY, gridUnitWidth, gridUnitHeight = detectGrid()

        for row in range(9):
            for column in range(9):
                if (unsolvedSudokuPuzzle[row][column] == 0):
                    tap(gridX + 10 + gridUnitWidth * column, gridY + 10 + gridUnitHeight * row)
                    tap(numberLocationDict[sudokuPuzzle[row][column]][0], numberLocationDict[sudokuPuzzle[row][column]][1])
        return True

    except:
        return False

if __name__ == "__main__":
    pytesseract.pytesseract.tesseract_cmd = r"C:/Path/To/tesseract.exe"

    banner()

    with yaspin(text="Loading Button Positions ...").line:
        numberLocationDict = findNumberLocations()
        
    if numberLocationDict == None:
        print("Loading Button Positions  " + color.color("Failed", 'fg_red'))
        print("Is your device plugged in?")
        input("Press enter to exit...")
        exit()
    elif numberLocationDict[1] == (None, None):
        print("Loading Button Positions  " + color.color("Failed", 'fg_red'))
        print("Have you opened the Sudoku app?")
        input("Press enter to exit...")
        exit()
    else:
        print("Loading Button Positions  " + color.color("Complete", 'fg_green'))
    

    with yaspin(text="Reading Puzzle Data ...").line:
        unsolvedPuzzle = readSudokuFromDeivce()
    print("Reading Puzzle Data  " + color.color("Complete", 'fg_green'))

    print("--------------------------")
    print("Puzzle Data:")
    printSudoku(unsolvedPuzzle)
    print("--------------------------")
    
    solvedPuzzle = [row[:] for row in unsolvedPuzzle]

    with yaspin(text="Solving puzzle ...").line:
        result = solveSudoku(solvedPuzzle)

    if (result):
        print("Solving puzzle  " + color.color("Complete", 'fg_green'))
        print("--------------------------")
        print("Solved Puzzle Data:")
        printSudoku(solvedPuzzle)
        print("--------------------------")
    else:
        print("Solving puzzle  " + color.color("Failed", 'fg_red'))
        input("Press enter to exit...")
        exit()

    with yaspin(text="Filling in puzzle ...").line:
        result = inputPuzzle(solvedPuzzle, unsolvedPuzzle, numberLocationDict)
    
    if (result):
        print("Filling in puzzle  " + color.color("Complete", 'fg_green'))
        input("Press enter to exit...")
        exit()
    else:
        print("Filling in puzzle  " + color.color("Failed", 'fg_red'))
        print("Is your device plugged in?")
        input("Press enter to exit...")
        exit()
    

