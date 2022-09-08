from waterpyk import main


def test_point():
    point = main.StudyArea([1111, 1111], 'minimal')
    assert point.kind == 'point', "Lat/Long not being categorized as 'point'"
    assert point.site_name == ''
    assert point.description == ''
    
    