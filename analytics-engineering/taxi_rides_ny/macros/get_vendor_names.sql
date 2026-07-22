-- macro which assigns value to respective vendor_id
{% macro get_vendor_names(vendor_id) %}

 case 
        when {{vendor_id}} = 1 then 'Creative Mobile Technologies, LLC'
        when {{vendor_id}} = 2 then 'VeriFone Inc.'
        When {{vendor_id}} = 4 then 'Unknown Vendor'
    end

{% endmacro %}
