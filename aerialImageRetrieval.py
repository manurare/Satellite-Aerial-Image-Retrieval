"""
__author__ = Linlin Chen
__email__ = lchen96@hawk.iit.edu


@Description:
This module is used to retrieve satellite/aerial image.
Given a bounding box, which is composed of left up corner coordinate (latitude, longitude) 
and right down corner coordinate (latitude, longitude).
Return an aerial imagery (with maximum resolution available) downloaded from Bing map tile system.

"""


import sys, io, os
from urllib import request
from PIL import Image
import csv
import matplotlib as plt

from tilesystem import TileSystem


BASEURL = "http://h0.ortho.tiles.virtualearth.net/tiles/h{0}.jpeg?g=131"
IMAGEMAXSIZE = 8192 * 8192 * 8 # max width/height in pixels for the retrived image
TILESIZE = 256              # in Bing tile system, one tile image is in size 256 * 256 pixels


class AerialImageRetrieval(object):
    """The class for aerial image retrieval

    To create an AerialImageRetrieval object, simply give upper left latitude, longitude,
    and lower right latitude and longitude
    """
    def __init__(self, lat1=0.0, lon1=0.0, lat2=0.0, lon2=0.0, coordinates_list=[]):
        if len(coordinates_list) == 0:
            coordinates_list.append([lat1, lon1, lat2, lon2])
            self.coordinates_list = coordinates_list
        else:
            self.coordinates_list = coordinates_list

        self.tgtfolder = './output/'
        try:
            os.makedirs(self.tgtfolder)
        except FileExistsError:
            pass
        except OSError:
            raise


    def download_image(self, quadkey):
        """This method is used to download a tile image given the quadkey from Bing tile system
        
        Arguments:
            quadkey {[string]} -- [The quadkey for a tile image]
        
        Returns:
            [Image] -- [A PIL Image]
        """

        with request.urlopen(BASEURL.format(quadkey)) as file:
            return Image.open(file)



    def is_valid_image(self, image):
        """Check whether the downloaded image is valid, 
        by comparing the downloaded image with a NULL image returned by any unsuccessfully retrieval

        Bing tile system will return the same NULL image if the query quadkey is not existed in the Bing map database.
        
        Arguments:
            image {[Image]} -- [a Image type image to be valided]
        
        Returns:
            [boolean] -- [whether the image is valid]
        """

        if not os.path.exists('null.png'):
            nullimg = self.download_image('11111111111111111111')      # an invalid quadkey which will download a null jpeg from Bing tile system
            nullimg.save('./null.png')
        return not (image == Image.open('./null.png'))



    def max_resolution_imagery_retrieval(self):
        """The main aerial retrieval method

        It will firstly determine the appropriate level used to retrieve the image.
        The appropriate level should satisfy:
            1. All the tile image within the given bounding box at that level should all exist
            2. The retrieved image cannot exceed the maximum supported image size, which is 8192*8192 (Otherwise the image size will be too large if the bounding box is very large)
        
        Then for the given level, we can download each aerial tile image, and stitch them together.

        Lastly, we have to crop the image based on the given bounding box

        Returns:
            [boolean] -- [indicate whether the aerial image retrieval is successful]
        """
        for idx, bbox in enumerate(self.coordinates_list):
            for levl in range(TileSystem.MAXLEVEL, 0, -1):
                pixelX1, pixelY1 = TileSystem.latlong_to_pixelXY(bbox[0], bbox[1], levl)
                pixelX2, pixelY2 = TileSystem.latlong_to_pixelXY(bbox[2], bbox[3], levl)

                pixelX1, pixelX2 = min(pixelX1, pixelX2), max(pixelX1, pixelX2)
                pixelY1, pixelY2 = min(pixelY1, pixelY2), max(pixelY1, pixelY2)


                #Bounding box's two coordinates coincide at the same pixel, which is invalid for an aerial image.
                #Raise error and directly return without retriving any valid image.
                if abs(pixelX1 - pixelX2) <= 1 or abs(pixelY1 - pixelY2) <= 1:
                    print("Cannot find a valid aerial imagery for the given bounding box!")
                    return

                if abs(pixelX1 - pixelX2) * abs(pixelY1 - pixelY2) > IMAGEMAXSIZE:
                    print("Current level {} results an image exceeding the maximum image size (8192 * 8192), will SKIP".format(levl))
                    continue

                tileX1, tileY1 = TileSystem.pixelXY_to_tileXY(pixelX1, pixelY1)
                tileX2, tileY2 = TileSystem.pixelXY_to_tileXY(pixelX2, pixelY2)

                # Stitch the tile images together
                result = Image.new('RGB', ((tileX2 - tileX1 + 1) * TILESIZE, (tileY2 - tileY1 + 1) * TILESIZE))
                retrieve_sucess = False
                for tileY in range(tileY1, tileY2 + 1):
                    retrieve_sucess, horizontal_image = self.horizontal_retrieval_and_stitch_image(tileX1, tileX2, tileY, levl)
                    if not retrieve_sucess:
                        break
                    result.paste(horizontal_image, (0, (tileY - tileY1) * TILESIZE))

                if not retrieve_sucess:
                    continue

                # Crop the image based on the given bounding box
                leftup_cornerX, leftup_cornerY = TileSystem.tileXY_to_pixelXY(tileX1, tileY1)
                retrieve_image = result.crop((pixelX1 - leftup_cornerX, pixelY1 - leftup_cornerY, \
                                            pixelX2 - leftup_cornerX, pixelY2 - leftup_cornerY))
                print("Finish the aerial image retrieval, store the image aerialImage_{0}_{1}.jpeg in folder {2}"
                      .format(idx, levl, self.tgtfolder))
                filename = os.path.join(self.tgtfolder, 'aerialImage_{}_{}.jpeg'.format(idx, levl))
                retrieve_image.save(filename)
                break
            


    def horizontal_retrieval_and_stitch_image(self, tileX_start, tileX_end, tileY, level):
        """Horizontally retrieve tile images and then stitch them together,
        start from tileX_start and end at tileX_end, tileY will remain the same
        
        Arguments:
            tileX_start {[int]} -- [the starting tileX index]
            tileX_end {[int]} -- [the ending tileX index]
            tileY {[int]} -- [the tileY index]
            level {[int]} -- [level used to retrieve image]
        
        Returns:
            [boolean, Image] -- [whether such retrieval is successful; If successful, returning the stitched image, otherwise None]
        """

        imagelist = []
        for tileX in range(tileX_start, tileX_end + 1):
            quadkey = TileSystem.tileXY_to_quadkey(tileX, tileY, level)
            image = self.download_image(quadkey)
            if self.is_valid_image(image):
                imagelist.append(image)
            else:
                #print(quadkey)
                print("Cannot find tile image at level {0} for tile coordinate ({1}, {2})".format(level, tileX, tileY))
                return False, None
        result = Image.new('RGB', (len(imagelist) * TILESIZE, TILESIZE))
        for i, image in enumerate(imagelist):
            result.paste(image, (i * TILESIZE, 0))
        return True, result
        


def main():
    """The main entrance.
    Decode the upper left and lower right coordinates, and retrieve the aerial image withing that bounding box  
    """

    # decode the bounding box coordinates
    try:
        args = sys.argv[1:]
    except IndexError:
        sys.exit('Diagonal (Latitude, Longitude) coordinates of the bounding box must be input')
    if len(args) != 4 and len(args) != 1:
        sys.exit('Please input Latitude, Longitude coordinates for both upper-left and lower-right corners!'
                 ' or add .csv file')
    try:
        if len(args) == 4:
            lat1, lon1, lat2, lon2 = float(args[0]), float(args[1]), float(args[2]), float(args[3])
        if len(args) == 1:
            coordinates_list = []
            csv_file = args[0]
            with open(csv_file, newline='') as csvfile:
                spamreader = csv.reader(csvfile, delimiter=',', skipinitialspace=True)
                for row in spamreader:
                    coordinates_list.append([float(row[0]), float(row[1]), float(row[2]), float(row[3])])
    except ValueError:
        sys.exit('Latitude and longitude must be float type')

    # Retrieve the aerial image
    if len(args) == 4:
        # lat1 = 41.882981
        # lon1 = - 87.623496
        # lat2 = 41.882397
        # lon2 = - 87.623076
        imgretrieval = AerialImageRetrieval(lat1=lat1, lon1=lon1, lat2=lat2, lon2=lon2)
    else:
        imgretrieval = AerialImageRetrieval(coordinates_list=coordinates_list)
    if imgretrieval.max_resolution_imagery_retrieval():
        print("Successfully retrieve the image with maximum resolution!")
    else:
        print("Cannot retrieve the desired image! (Possible reason: expected tile image does not exist.)")


if __name__ == '__main__':
    main()

