if(CONFIG_SHIELD_NICE_VIEW_ART)
  target_sources(app PRIVATE
    ${CMAKE_CURRENT_LIST_DIR}/custom_status_screen.c
    ${CMAKE_CURRENT_LIST_DIR}/art.c
  )
endif()
