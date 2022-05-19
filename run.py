from waterpyk import studyarea
from waterpyk.extract.watershed import metadata
from waterpyk.studyarea.studyarea import StudyArea
import pandas as pd

if __name__ == "__main__":

    gage = [11475560]
    coords = [39.7273, -123.6433]

    layers_path = '/Users/ericamccormick/Documents/GITHUB/WaterPyk/data/production/layers_long_contemporary_2021.csv'
    layers = pd.read_csv(layers_path)

    #elder = StudyArea(gage, layers)
    #print(elder.smax)

    rivendell = StudyArea(coords, layers)
    print(rivendell.smax)


