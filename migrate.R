library(dplyr)

data <- read.csv("data/um24_umlandsurvey.csv")

import <- data.frame(identifier = ifelse(data$find_id == "", NA, data$find_id))
import$date <- format.Date(data$today, "%d.%m.%Y")
import$scanCode <- data$find_id
import$amount <- data$find_quantity
import$spatialLocation <- paste("Ground Visibility:", data$ground_visibility,
                                "\\nGeopoint Accuracy:", data$geopoint.Accuracy,
                                "\\nDevive / User:", data$username)
# #TODO: This does not actually work, somehow.
#import$dimensionVerticalExtent.0.inputValue	<- round(data$geopoint.Altitude, digits = 2)
#import$dimensionVerticalExtent.0.inputRangeEndValue <- ""
#import$dimensionVerticalExtent.0.inputUnit	<- "m"
#import$dimensionVerticalExtent.0.measurementPosition <- ""
#import$dimensionVerticalExtent.0.measurementComment.de <- paste("Geopoint Accuracy:", data$geopoint.Accuracy)
#import$dimensionVerticalExtent.0.isImprecise <- "false"


import$relations.isRecordedIn <- "Test-Pergamon-Ludwig"
import$shortDescription <- data$find_type
import$description <- data$comment
import$processor <- data$username

unique(data$username)
table(data$find_type)

import$category <- data$find_type
import$category <- gsub("ceramic / pottery", "Pottery", import$category)
import$category <- gsub("stone finds", "Stone", import$category)
import$category <- gsub("tiles / bricks", "Brick", import$category)
import$category <- gsub("small finds", "Find", import$category)
import$category <- gsub("other", "Find", import$category)
import$category <- gsub("terracotta finds", "Terracotta", import$category)
import$category <- gsub("water pipes", "Find", import$category)
import$category <- gsub("marble", "Stone", import$category)
import$category <- gsub("coins", "Coin", import$category)
import$category <- gsub("production manufacture", "Find", import$category)
import$category <- gsub("metal objects", "Metal", import$category)



# identify duplicate names / scanCodes
dupl <- table(import$identifier)[table(import$identifier) > 1]
dupl

# save csv by category
for (cat in unique(import$category)) {
  thisCat <- import %>%
    filter(!is.na(identifier)) %>%
    filter(category == cat) %>%
    select(!category)

  dupl <- match(names(dupl), thisCat$identifier)

  if (nrow(thisCat) > 0) {
    # save duplicates in extra file to check
    if (length(dupl) > 0) {
      write.csv(thisCat[-dupl, ], file = paste0('out/import.', cat, '.csv'), row.names = FALSE, quote = FALSE)
      write.csv(thisCat[dupl, ], file = paste0('out/import.', cat, '_duplicates.csv'), row.names = FALSE, quote = FALSE)
    } else {
      write.csv(thisCat, file = paste0('out/import.', cat, '.csv'), row.names = FALSE, quote = FALSE)
    }
  }
}


# Geodata

library(sf)
geodata <- data %>%
  filter(find_id != "") %>%
  select(geopoint.Longitude, geopoint.Latitude, find_id) %>%
  rename(identifier = find_id)

geodata <- st_as_sf(geodata, coords = c("geopoint.Longitude", "geopoint.Latitude"), crs = 4326)

# set to UTM35N = EPSG 32635
geodata <- st_transform(geodata, 32635)
#plot(geodata)

st_write(geodata, "out/Field.Points.geojson", driver = "GeoJSON", append = FALSE)
