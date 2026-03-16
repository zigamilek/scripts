# By Ziga Milek, 26.2.2020
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from random import randint

SERIES_ROOT = os.getenv("KODI_SERIES_ROOT", "/Volumes/eulerShare/Series").rstrip("/")
LEGACY_SERIES_ROOT = "/Volumes/eulerShare/Series/"

file_paths = [
    "/Volumes/eulerShare/Series/Grand Designs/Season 01/Grand.Designs.S01.DVDRip.AC3.2.0.x264-BTN/Grand.Designs.S01E01.Newhaven.The.Timber.Frame.Kit.House.DVDRip.AC3.2.0.x264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 01/Grand.Designs.S01.DVDRip.AC3.2.0.x264-BTN/Grand.Designs.S01E02.Berkshire.English.Barn.DVDRip.AC3.2.0.x264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 01/Grand.Designs.S01.DVDRip.AC3.2.0.x264-BTN/Grand.Designs.S01E03.Brighton.The.Co.Operative.Build.DVDRip.AC3.2.0.x264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 01/Grand.Designs.S01.DVDRip.AC3.2.0.x264-BTN/Grand.Designs.S01E04.Amersham.The.Water.Tower.DVDRip.AC3.2.0.x264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 01/Grand.Designs.S01.DVDRip.AC3.2.0.x264-BTN/Grand.Designs.S01E05.Suffolk.The.Eco.House.DVDRip.AC3.2.0.x264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 01/Grand.Designs.S01.DVDRip.AC3.2.0.x264-BTN/Grand.Designs.S01E06.Cornwall.The.Chapel.DVDRip.AC3.2.0.x264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 01/Grand.Designs.S01.DVDRip.AC3.2.0.x264-BTN/Grand.Designs.S01E07.Islington.The.House.of.Straw.DVDRip.AC3.2.0.x264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 01/Grand.Designs.S01.DVDRip.AC3.2.0.x264-BTN/Grand.Designs.S01E08.Doncaster.The.Glass.House.DVDRip.AC3.2.0.x264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 02/Grand Designs - S02E01 - Farnham - The Regency Villa.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 02/Grand Designs - S02E02 - Sussex - The New England Gable House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 02/Grand Designs - S02E03 - Netherton - The Wool Mill.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 02/Grand Designs - S02E04 - Brecon Beacons - The Isolated Cottage.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 02/Grand Designs - S02E05 - Lambourn Valley - The Cruciform House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 02/Grand Designs - S02E06 - Birmingham - The Self-Build.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 02/Grand Designs - S02E07 - London - The Jewel Box.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 02/Grand Designs - S02E08 - Devon - The Derelict Barns.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 02/Grand Designs - S02E09 - Revisited - Doncaster - The Glass-House (Revisited from S1 Ep8).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 02/Grand Designs - S02E10 - Revisited - Suffolk - The Eco-House (Revisited from S1 Ep5).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 02/Grand Designs - S02E11 - Revisited - Islington - The House of Straw (Revisited from S1 Ep7).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 02/Grand Designs - S02E12 - Revisited - Birmingham - The Self-Build (Revisited from S2 Ep6).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 02/Grand Designs - S02E13 - Revisited - Brighton - The Co-Op (Revisited from S1 Ep3).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 02/Grand Designs - S02E14 - Revisited - Brecon Beacons Wales - The Isolated Cottage (Revisited from S2 Ep4).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 02/Grand Designs - S02E15 - Revisited - London - The Dilapidated Georgian House (Revisited from Grand Designs Indoors - 15 March 2001).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 02/Grand Designs - S02E16 - Revisited - Coleshill Amersham - The Water Tower (Revisited from S1 Ep4).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 02/Grand Designs - S02E17 - Revisited - Devon - The Derelict Barns (Revisited from S2 Ep8).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 03/Grand Designs - S03E01 - Peterborough - The Wooden Box.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 03/Grand Designs - S03E02 - Chesterfield - The Water-Works.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 03/Grand Designs - S03E03 - Sussex - The Woodsmans Cottage.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 03/Grand Designs - S03E04 - Surrey - The Victorian Threshing Barn.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 03/Grand Designs - S03E06 - Hackney - The Terrace Conversion.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 03/Grand Designs - S03E07 - Cumbria - The Underground House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 03/Grand Designs - S03E08 - Herefordshire - The Traditional Cottage.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 03/Grand Designs - S03E11 - Revisited - Sunderland - The Former Electricity Sub-Station (Revisited from Grand Designs Indoors - 1 March 2001).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 03/Grand Designs - S03E12 - Revisited - Berkshire - The English Barn (Revisited from S1 Ep2).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 04/Grand Designs - S04E01 - Lambeth - The Violin Factory.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 04/Grand Designs - S04E02 - Walton on Thames - Customised German Kit House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 04/Grand Designs - S04E03 - Revisited - Buckinghamshire - The Inverted-Roof House (Revisited from S3 Ep5).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 04/Grand Designs - S04E04 - Leith - 19th Century Sandstone House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 04/Grand Designs - S04E05 - Clapham - The Curved House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 04/Grand Designs - S04E06 - Sussex - The Modernist Sugar Cube.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 04/Grand Designs - S04E07 - Argyll - The Oak-Framed House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 04/Grand Designs - S04E08 - Dorset - An Idiosyncratic Home.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 05/Grand.Designs.S05.DVDRip.AC3.2.0.x264-BTN/Grand.Designs.S05E02.Peckham.The.Sliding.Glass.Roof.House.DVDRip.AC3.2.0.x264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 05/Grand.Designs.S05.DVDRip.AC3.2.0.x264-BTN/Grand.Designs.S05E03.Gloucester.The.16th.Century.Farmhouse.DVDRip.AC3.2.0.x264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 05/Grand.Designs.S05.DVDRip.AC3.2.0.x264-BTN/Grand.Designs.S05E04.Kent.Finnish.Log.Cabin.DVDRip.AC3.2.0.x264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 05/Grand.Designs.S05.DVDRip.AC3.2.0.x264-BTN/Grand.Designs.S05E07.Devon.Shaped.Like.a.Curvy.Seashell.DVDRip.AC3.2.0.x264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 05/Grand.Designs.S05.DVDRip.AC3.2.0.x264-BTN/Grand.Designs.S05E09.Belfast.A.21st.Century.Answer.to.the.Roman.Villa.DVDRip.AC3.2.0.x264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 05/Grand.Designs.S05.DVDRip.AC3.2.0.x264-BTN/Grand.Designs.S05E10.Devon.Miami.Style.Beach.House.DVDRip.AC3.2.0.x264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 05/Grand.Designs.S05.DVDRip.AC3.2.0.x264-BTN/Grand.Designs.S05E11.Carmarthen.The.Eco-House.DVDRip.AC3.2.0.x264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 05/Grand Designs - S05E05 - Revisited - Hackney - The Terrace Conversion (Revisited from S3 Ep6).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 06/Grand.Designs.S06.DVDRip.AAC2.0.H.264-BTN/Grand.Designs.S06E01.Killearn.The.Loch.House.DVDRip.AAC2.0.H.264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 06/Grand.Designs.S06.DVDRip.AAC2.0.H.264-BTN/Grand.Designs.S06E02.Ross-On-Wye.The.Contemporary.Barn.Conversion.DVDRip.AAC2.0.H.264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 06/Grand.Designs.S06.DVDRip.AAC2.0.H.264-BTN/Grand.Designs.S06E03.Stirling.The.Contemporary.Cedar.Clad.Home.DVDRip.AAC2.0.H.264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 06/Grand.Designs.S06.DVDRip.AAC2.0.H.264-BTN/Grand.Designs.S06E04.Ashford.Water.Tower.Conversion.DVDRip.AAC2.0.H.264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 06/Grand.Designs.S06.DVDRip.AAC2.0.H.264-BTN/Grand.Designs.S06E07.Exeter.Split.Personality.House.DVDRip.AAC2.0.H.264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 07/Grand.Designs.S07.DVDRip.AAC2.0.H.264-BTN/Grand.Designs.S07E01.Yorkshire.The.14th.Century.Castle.DVDRip.AAC2.0.H.264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 07/Grand.Designs.S07.DVDRip.AAC2.0.H.264-BTN/Grand.Designs.S07E02.Hampshire.The.Thatched.Cottage.DVDRip.AAC2.0.H.264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 07/Grand.Designs.S07.DVDRip.AAC2.0.H.264-BTN/Grand.Designs.S07E03.Medway.The.Eco-Barge.DVDRip.AAC2.0.H.264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 07/Grand.Designs.S07.DVDRip.AAC2.0.H.264-BTN/Grand.Designs.S07E04.Bournemouth.The.Bournemouth.Penthouse.DVDRip.AAC2.0.H.264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 07/Grand.Designs.S07.DVDRip.AAC2.0.H.264-BTN/Grand.Designs.S07E06.Birmingham.The.Birmingham.Church.DVDRip.AAC2.0.H.264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 07/Grand.Designs.S07.DVDRip.AAC2.0.H.264-BTN/Grand.Designs.S07E07.Guildford.The.Art.Deco.House.DVDRip.AAC2.0.H.264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 07/Grand.Designs.S07.DVDRip.AAC2.0.H.264-BTN/Grand.Designs.S07E10.Cambridge.The.Cambridgeshire.Eco.Home.DVDRip.AAC2.0.H.264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 07/Grand.Designs.S07.DVDRip.AAC2.0.H.264-BTN/Grand.Designs.S07E12.London.The.Glass.and.Timber.House.DVDRip.AAC2.0.H.264-BTN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 07/Grand Designs - S07E05 - Revisited - Carmarthen - The Eco-House (Revisited from S5 Ep11).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 07/Grand Designs - S07E08 - Revisited - Peckham - The Sliding Glass Roof House (Revisited from S5 Ep2).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 07/Grand Designs - S07E09 - Revisited - Argyll - The Oak-Framed House (Revisited from S4 Ep7).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 07/Grand Designs - S07E11 - Revisited - Tuscany - The Tuscan Castle (Revisited from Grand Designs Abroad - 13 October 2004).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 08/Grand Designs - S08E01 - Cheltenham - The Underground House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 08/Grand Designs - S08E02 - Oxford - The Decagon House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 08/Grand Designs - S08E03 - Bristol - The Modernist Sugar Cube.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 08/Grand Designs - S08E04 - Herefordshire - The Gothic House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 08/Grand Designs - S08E05 - Midlothian - The Lime Kiln House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 08/Grand Designs - S08E06 - Bath - The Bath Kit House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 08/Grand Designs - S08E07 - Revisited - Puglia - An Artists Retreat (Revisited from Grand Designs Abroad - 22 September 2004).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 08/Grand Designs - S08E08 - Revisited - Peterborough - The Wooden Box (Revisited from S3 Ep1).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 08/Grand Designs - S08E09 - Revisited - Surrey - Customised German Kit House (Revisited from S4 Ep2).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 08/Grand Designs - S08E10 - Revisited - Surrey - The Victorian Threshing Barn (Revisited from S3 Ep4).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 08/Grand Designs - S08E11 - Revisited - Cumbria - The Underground House (Revisited from S3 Ep7).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 08/Grand Designs - S08E12 - Maidstone - The Hi Tech Bungalow.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 09/Grand Designs - S09E01 - Somerset - The Apprentice Store.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 09/Grand Designs - S09E02 - Oxfordshire - The Chilterns Water Mill.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 09/Grand Designs - S09E03 - Newport - The Newport Folly.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 09/Grand Designs - S09E04 - Kent - The Eco Arch.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 09/Grand Designs - S09E05 - Brittany - The Brittany Groundhouse.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 09/Grand Designs - S09E06 - Wiltshire - The Marlborough Farm House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 09/Grand Designs - S09E07 - Kent - The Headcorn Minimalist House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 09/Grand Designs - S09E08 - Revisited - The 14th Century Castle (Revisited from S7 Ep1).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 09/Grand Designs - S09E09 - Revisited - Cambridgeshire - The Cambridgeshire Eco Home (Revisited from S7 Ep10).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 09/Grand Designs - S09E10 - Brighton - The Brighton Modern Mansion.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 09/Grand Designs - S09E11 - Revisited - Hampshire - The Thatched Cottage (Revisited from S7 Ep2).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 09/Grand Designs - S09E12 - Revisited - Killearn Scotland - The Loch House (Revisited from S6 Ep1).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 09/Grand Designs - S09E13 - 2nd Revisit - Sussex - The Woodsmans Cottage (Revisited from S3 Ep3 & S5 Ep8).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 10/Grand Designs - S10E01 - Isle of Wight - The Tree House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 10/Grand Designs - S10E02 - Cotswolds - The Stealth House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 10/Grand Designs - S10E03 - Woodbridge - The Modest Home.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 10/Grand Designs - S10E04 - Stowmarket - The Barn & Guildhall.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 10/Grand Designs - S10E05 - Ipswich - The Radian House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 10/Grand Designs - S10E06 - Lizard Peninsular - The Scandinavian House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 10/Grand Designs - S10E07 - Cumbria - The Adaptahaus.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 10/Grand Designs - S10E08 - Lake District - The Dome House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 10/Grand Designs - S10E09 - Revisited - Brittany France - The Brittany Groundhouse (Revisited from S9 Ep5).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 10/Grand Designs - S10E10 - Revisited - Dulwich - The Glass & Timber House (Revisited from S7 Ep12).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 10/Grand Designs - S10E11 - Revisited - Belfast - A 21st Century Answer to the Roman Villa (Revisited from S5 Ep9).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 10/Grand Designs - S10E12 - Revisited - Lot France - House from Straw (Revisited from Grand Designs Abroad - 15 September 2004).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 10/Grand Designs - S10E13 - Coleshill Amersham - 2nd Revisit - The Water Tower (Revisited from S1 Ep4 and S2 Ep16).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 10/Grand Designs - S10E14 - Revisited - Midlothian Scotland - The Lime Kiln House (Revisited from S8 Ep5).nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 11/Grand Designs - S11E01 - Morpeth - The Derelict Mill Cottage.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 11/Grand Designs - S11E02 - London - The Contemporary Mansion.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 11/Grand Designs - S11E03 - Tenby - The Lifeboat Station.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 11/Grand Designs - S11E04 - Essex - The Large Timber-framed Barn.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 11/Grand Designs - S11E05 - Herefordshire - The Recycled Timber-framed House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 11/Grand Designs - S11E06 - Cornwall - The Dilapidated Engine House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 11/Grand Designs - S11E07 - London - The Disco Home.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 11/Grand Designs - S11E08 - Revisited - Lake District - The Dome House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 11/Grand Designs - S11E09 - Revisited - Kent - The Eco Arch.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 11/Grand Designs - S11E10 - Revisited - Ashford Kent - The Water Tower Conversion.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 11/Grand Designs - S11E11 - Revisited - Cumbria - The Adaptahaus.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 11/Grand Designs - S11E12 - Revisited - Kent - The Headcorn Minimalist House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 12/Grand Designs - S12E01 - Roscommon Ireland - Cloontykilla Castle.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 12/Grand Designs - S12E02 - Hertfordshire - The Computer-cut House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 12/Grand Designs - S12E03 - Brixton - The Glass Cubes House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 12/Grand Designs - S12E04 - Oxfordshire - The Thames Boathouse.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 12/Grand Designs - S12E05 - London - The Derelict Water Tower.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 12/Grand Designs - S12E06 - London - The Underground House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 12/Grand Designs - S12E07 - Isle of Skye - The Larch-Clad House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 12/Grand Designs - S12E08 - London - The Joinery Workshop.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 12/Grand Designs - S12E09 - Revisited - Isle of Wight - The Tree House.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 12/Grand Designs - S12E10 - Revisited - London - The Disco Home.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 12/Grand Designs - S12E11 - Revisited - Essex - The Large Timber-Framed Barn.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 12/Grand Designs - S12E12 - 2nd Revisiting - Brighton - The Co-Op.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 13/Grand.Designs.S13.720p.HDTV.x264-C4TV/grand.designs.s13e01.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 13/Grand.Designs.S13.720p.HDTV.x264-C4TV/grand.designs.s13e02.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 13/Grand.Designs.S13.720p.HDTV.x264-C4TV/grand.designs.s13e03.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 13/Grand.Designs.S13.720p.HDTV.x264-C4TV/grand.designs.s13e04.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 13/Grand.Designs.S13.720p.HDTV.x264-C4TV/grand.designs.s13e05.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 13/Grand.Designs.S13.720p.HDTV.x264-C4TV/grand.designs.s13e06.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 13/Grand.Designs.S13.720p.HDTV.x264-C4TV/grand.designs.s13e07.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 13/Grand.Designs.S13.720p.HDTV.x264-C4TV/grand.designs.s13e08.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 13/Grand.Designs.S13.720p.HDTV.x264-C4TV/grand.designs.s13e09.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 13/Grand.Designs.S13.720p.HDTV.x264-C4TV/grand.designs.s13e10.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 13/Grand.Designs.S13.720p.HDTV.x264-C4TV/grand.designs.s13e11.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 14/Grand.Designs.S14.720p.HDTV.x264-C4TV/grand.designs.s14e01.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 14/Grand.Designs.S14.720p.HDTV.x264-C4TV/grand.designs.s14e02.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 14/Grand.Designs.S14.720p.HDTV.x264-C4TV/grand.designs.s14e03.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 14/Grand.Designs.S14.720p.HDTV.x264-C4TV/grand.designs.s14e04.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 14/Grand.Designs.S14.720p.HDTV.x264-C4TV/grand.designs.s14e05.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 14/Grand.Designs.S14.720p.HDTV.x264-C4TV/grand.designs.s14e06.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 14/Grand.Designs.S14.720p.HDTV.x264-C4TV/grand.designs.s14e07.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 14/Grand.Designs.S14.720p.HDTV.x264-C4TV/grand.designs.s14e08.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 14/Grand.Designs.S14.720p.HDTV.x264-C4TV/grand.designs.s14e09.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 14/Grand.Designs.S14.720p.HDTV.x264-C4TV/grand.designs.s14e10.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 15/Grand.Designs.S15.720p.HDTV.x264-C4TV/grand.designs.s15e01.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 15/Grand.Designs.S15.720p.HDTV.x264-C4TV/grand.designs.s15e02.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 15/Grand.Designs.S15.720p.HDTV.x264-C4TV/grand.designs.s15e03.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 15/Grand.Designs.S15.720p.HDTV.x264-C4TV/grand.designs.s15e04.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 16/Grand.Designs.S16.720p.HDTV.x264-C4TV/grand.designs.s16e01.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 16/Grand.Designs.S16.720p.HDTV.x264-C4TV/grand.designs.s16e02.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 16/Grand.Designs.S16.720p.HDTV.x264-C4TV/grand.designs.s16e03.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 16/Grand.Designs.S16.720p.HDTV.x264-C4TV/grand.designs.s16e04.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 16/Grand.Designs.S16.720p.HDTV.x264-C4TV/grand.designs.s16e05.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 16/Grand.Designs.S16.720p.HDTV.x264-C4TV/grand.designs.s16e06.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 16/Grand.Designs.S16.720p.HDTV.x264-C4TV/grand.designs.s16e07.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 16/Grand.Designs.S16.720p.HDTV.x264-C4TV/grand.designs.s16e08.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 16/Grand.Designs.S16.720p.HDTV.x264-C4TV/grand.designs.s16e09.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 17/Grand.Designs.S17.720p.HDTV.x264-BTN/grand.designs.s17e01.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 17/Grand.Designs.S17.720p.HDTV.x264-BTN/Grand.Designs.S17E02.720p.HDTV.x264-C4TV.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 17/Grand.Designs.S17.720p.HDTV.x264-BTN/grand.designs.s17e03.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 17/Grand.Designs.S17.720p.HDTV.x264-BTN/grand.designs.s17e04.720p.hdtv.x264-c4tv.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 17/Grand.Designs.S17.720p.HDTV.x264-BTN/Grand.Designs.S17E05.720p.HDTV.x264-C4TV.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 17/Grand.Designs.S17.720p.HDTV.x264-BTN/Grand.Designs.S17E06.720p.HDTV.x264-C4TV.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 17/Grand.Designs.S17.720p.HDTV.x264-BTN/Grand.Designs.S17E07.720p.HDTV.x264-BEGUN.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 17/Grand.Designs.S17.720p.HDTV.x264-BTN/Grand.Designs.S17E08.720p.HDTV.x264-C4TV.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 17/Grand.Designs.S17E09.HDTV.x264-GTi.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 18/Grand.Designs.S18.1080p.HDTV.AAC2.0.x264-PLUTONiUM/grand.designs.s18e01.1080p.hdtv.h264-plutonium.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 18/Grand.Designs.S18.1080p.HDTV.AAC2.0.x264-PLUTONiUM/grand.designs.s18e02.1080p.hdtv.h264-plutonium.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 18/Grand.Designs.S18.1080p.HDTV.AAC2.0.x264-PLUTONiUM/grand.designs.s18e03.1080p.hdtv.h264-plutonium.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 18/Grand.Designs.S18.1080p.HDTV.AAC2.0.x264-PLUTONiUM/grand.designs.s18e04.1080p.hdtv.h264-plutonium.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 18/Grand.Designs.S18.1080p.HDTV.AAC2.0.x264-PLUTONiUM/grand.designs.s18e05.1080p.hdtv.h264-plutonium.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 18/Grand.Designs.S18.1080p.HDTV.AAC2.0.x264-PLUTONiUM/grand.designs.s18e06.1080p.hdtv.h264-plutonium.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 18/Grand.Designs.S18.1080p.HDTV.AAC2.0.x264-PLUTONiUM/grand.designs.s18e07.1080p.hdtv.h264-plutonium.nfo",
    "/Volumes/eulerShare/Series/Grand Designs/Season 18/Grand.Designs.S18.1080p.HDTV.AAC2.0.x264-PLUTONiUM/grand.designs.s18e08.1080p.hdtv.h264-plutonium.nfo"
]

file_paths = [
    path.replace(LEGACY_SERIES_ROOT, f"{SERIES_ROOT}/", 1)
    if path.startswith(LEGACY_SERIES_ROOT)
    else path
    for path in file_paths
]

for file_path in file_paths:
    print("Working on: " + file_path + "\n")

    tree = ET.parse(file_path)
    root = tree.getroot()
    # root_str = ET.tostring(root, encoding='unicode',
    #                        method='xml').replace('\n', '')
    # print(root_str)

    if root.find('uniqueid') is not None:
        print("  Already has uniqueid. Skipping...")
        continue

    thumb_url = root.find('thumb').text
    # print(thumb_url)

    if thumb_url is None:
        uniqueid = str(randint(10000, 99999))
        uniqueid_element = ET.SubElement(
            root, 'uniqueid', {'type': 'ziga', 'default': 'true'})
    else:
        uniqueid = thumb_url.rsplit('/', 1)[-1].rsplit('.', 1)[0]
        # print(uniqueid)

        uniqueid_element = ET.SubElement(
            root, 'uniqueid', {'type': 'tvdb', 'default': 'true'})

    uniqueid_element.text = uniqueid
    # ET.dump(root)

    # print(uniqueid_element.text)

    # tree = lxml.etree.parse("small.xml")

    # xmlstr = lxml.etree.tostring(ET.tostring(
    # root), encoding="unicode", pretty_print=True)

    xmlstr = minidom.parseString(ET.tostring(
        root, encoding='unicode', method='xml').replace('\n', '')).toprettyxml(indent="   ")
    # with open(dir_path + '/bla.nfo', "w") as f:
    with open(file_path, "w") as f:
        f.write(xmlstr)

    # tree.write()
