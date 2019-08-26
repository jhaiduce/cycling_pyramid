function parseDate(datestr) {
    var [datestr,timestr]=datestr.split(" ")
    var [y,mon,d]=datestr.split("-").map(parseFloat)
    var [h,min,s]=timestr.split(":").map(parseFloat)
    return new Date(y,mon-1,d,h,min,s)
}

function time_string_to_seconds(str){
    tokens=str.split(':')
    if(tokens.length!=3) throw Error("Invalid time string")
    try{
	var [h,m,s]=tokens.map(parseFloat)
    }
    catch(err){
	throw Error("Invalid time string")
    }
    
    return (h*3600+m*60+s)
}

$(function() {

    jQuery.validator.addMethod('end_time_after_start_time',function(value,element){
	try{
	    start_time=parseDate($("input[name='start_time']").val())
	    end_time=parseDate($("input[name='end_time']").val())
	}
	catch(err){
	    return true;
	}

	if(start_time<end_time) return true;
	else return false;

    },'End time should be after start time')

    jQuery.validator.addMethod('check_total_time_consistent',function(value,element){
	try{
	    start_time=parseDate($("input[name='start_time']").val())
	    end_time=parseDate($("input[name='end_time']").val())
	}
	catch(err){
	    return true;
	}

	interval_s=(end_time-start_time)/1000

	try{
	    total_time_s=time_string_to_seconds($("input[name='total_time']").val())
	}
	catch(err){
	    return true
	}

	delta=Math.abs(interval_s-total_time_s)

	if(delta<60) return true;
	else return false;

    },'Total time is inconsistent with start and end times')
    
    jQuery.validator.addMethod('check_total_time_gte_rolling_time',function(value,element){
	try{
	    total_time_s=time_string_to_seconds($("input[name='total_time']").val())
	    rolling_time_s=time_string_to_seconds($("input[name='rolling_time']").val())
	}
	catch(err){
	    return true
	}

	if(rolling_time_s<total_time_s) return true;
	else return false;

    },'Total time should be greater than rolling time')
    
    jQuery.validator.addMethod('avspeed_consistent',function(value,element){
	try{
	    distance=parseFloat($("input[name='distance']").val())
	}
	catch(TypeError){
	    return true;
	}
	try{
	    hours=time_string_to_seconds($("input[name='rolling_time']").val())/3600.0
	}
	catch(err){
	    return true;
	}

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
	    start_time:{
		end_time_after_start_time:true,
		check_total_time_consistent:true
	    },
	    end_time:{
		end_time_after_start_time:true,
		check_total_time_consistent:true
	    },
	    total_time:{
		check_total_time_consistent:true,
		check_total_time_gte_rolling_time:true
	    },
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
	    },
	    rolling_time:{
		avspeed_consistent:true,
		check_total_time_gte_rolling_time:true
	    }
	},
    });
});
