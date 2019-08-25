$(function() {

    jQuery.validator.addMethod('avspeed_consistent',function(value,element){
	try{
	    distance=parseFloat($("input[name='distance']").val())
	}
	catch(TypeError){
	    return true;
	}
	try{
	    t=$("input[name='rolling_time']").val().split(':').map(parseFloat)
	}
	catch(TypeError){
	    return true;
	}
	hours=t[0]+t[1]/60.0+t[2]/3600.0
	calcspeed=distance/hours
	ratio=value/calcspeed
	if(ratio<0.99 || ratio>1.02) return false;
	else return true;
    },'Average speed is inconsistent with the time and distance entered');
    
    jQuery.validator.addMethod('checkMaxspeedGteAvspeed',function(value,element){
	try{
	    avspeed=parseFloat($("input[name='avspeed']").val())
	}
	catch(TypeError){
	    return true;
	}
	try{
	    maxspeed=parseFloat($("input[name='maxspeed']").val())
	}
	catch(TypeError){
	    return true;
	}
	if(maxspeed>avspeed) return true;
	else return false;
    },'Max speed should be greater than average speed.');
    
    jQuery.validator.addMethod('checkOdometerDistance',function(value,element){
	try{
	    distance=parseFloat($("input[name='distance']").val())
	}
	catch(TypeError){
	    return true;
	}
	try{
	    odometer=parseFloat($("input[name='odometer']").val())
	}
	catch(TypeError){
	    return true;
	}
	equipment_id=parseInt($("select[name='equipment'] option:selected").val())
	start_time=$("input[name='start_time']").val()

	$.ajax({
	    url:'/rides/last_odo?equipment_id='+equipment_id+'&start_time='+start_time,
	    async:false,
	    dataType: 'json',
	    success:function(result){
		odometer_last=result.odometer
	    }});
	if(Math.abs(odometer_last+distance-odometer)>0.1){
	    return false;
	}
	else return true;
    },'Odometer value and ride distance do not match');

  // Initialize form validation on the registration form.
  // It has the name attribute "registration"
    $("form[id='deform']").validate({
	onsubmit:false,
	rules:{
	    distance:{
		min:0,
		number:true,
		checkOdometerDistance:true
	    },
	    odometer:{
		min:0,
		number:true,
		checkOdometerDistance:true
	    },
	    maxspeed:{
		min:0,
		number:true,
		checkMaxspeedGteAvspeed:true
	    },
	    avspeed:{
		min:0,
		number:true,
		avspeed_consistent:true,
		checkMaxspeedGteAvspeed:true
	    }
	},
    });
});
