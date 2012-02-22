

ST.table = function() {

  function set_html(container_id)
  {
      return function(result, textStatus, jqXHR) {
          var container = $(ST.dialogs.jquery_id(container_id));
          container.html(result);
      }
  };

  function replace_item(container_id, item_value)
  {
      return function(result, textStatus, jqXHR) {
          var container = $(ST.dialogs.jquery_id(container_id));
          var button = container.find('table button[value="'+item_value+'"]');
          var row = button.closest('tr');
          if (result) {
              row.replaceWith(result);
          } else {
              button.parent().children().remove();
              row.fadeTo(200, 0.1);
          }
      }
  };

  function container_form_submit_data(container_id, url, data, method)
  {
      var container = $(ST.dialogs.jquery_id(container_id));
      var form = container.find('form');

      if (!method) method = "GET";

      var request = $.ajax({
          type: "POST",
          url: url,
          data: data,
          });
      return request;
  };

  function container_form_submit(container_id, button, extra_data)
  {
      var container = $(ST.dialogs.jquery_id(container_id));
      var form = container.find('form');

      data = form.serializeArray();

      if (button) {
          var element = $(button);
          data.push({
            name: element.attr('name'),
            value: element.attr('value')});
      }

      if (extra_data) {
          data.push.apply(data, extra_data);
      }

      return container_form_submit_data(
               container_id, form.attr('action'), data, 'POST');
  };

  function add_counter(target, name, promise) {
      var counter = target.data(name);
      if (!counter) {
          counter = $.Deferred();
          counter.count = 0;
          target.data(name, counter);
          counter.done(function(){
              target.removeData(name);
          })
      }
      counter.count++;
      counter.notify(counter.count);
      promise.done( function(){
          counter.count--;
          counter.notify(counter.count);
          if (!counter.count) {
              counter.resolve();
          };
      });
      return counter;
  };

  function show_table_spinner(container_id, request) {
      var container = $(ST.dialogs.jquery_id(container_id));
      var counter = add_counter(container, 'st-table-counter', request);

      if (counter.count == 1) {
          // it's a new counter
          counter.progress( function(count){
              var container = $(ST.dialogs.jquery_id(container_id));
              var last_header = container.find('table.data>thead th:last');
              if (!last_header)
                  return;
              var spinner_id = container_id+'-table-spinner';
              var spinner = last_header.find(ST.dialogs.jquery_id(spinner_id));
              if ((spinner.length>0) && (count<=0)) {
                  spinner.remove()
              }
              if ((count>0) && (spinner.length==0)) {
                  spinner = ST.images.spinner();
                  spinner.addClass('st-table-spinner');
                  spinner.attr('id', spinner_id);
                  last_header.append(spinner);
              }

          });
      }

  }

  function show_button_spinner(container_id, button_value) {
      var container = $(ST.dialogs.jquery_id(container_id));
      var button = container.find('table button[value="'+button_value+'"]');
      button.hide();
      var spinner = ST.images.spinner();
      spinner.css('class', 'st-table-button-spinner')
      button.parent().append(spinner);
  }

  return {
      on_form_submit: function(container_id, button, extra_data) {
          var request = container_form_submit(container_id, button, extra_data);
          request.success(set_html(container_id));
          show_table_spinner(container_id, request);
          return false;
      },

      on_item_submit: function(container_id, button, extra_data) {
          var element = $(button);
          var item_value = element.attr('value');
          show_button_spinner(container_id, item_value);
          var request = container_form_submit(container_id, button, extra_data);
          request.success(replace_item(container_id, item_value));
          show_table_spinner(container_id, request);
          return false;
      },

      on_form_sort: function(container_id, column_name, sort_on_name) {
          var field = $(ST.dialogs.jquery_id(sort_on_name));
          if (field.val()) {
              field.val(field.val() + ' ' + column_name);
          } else {
              field.val(column_name);
          };

          var request = container_form_submit(container_id);
          request.success(set_html(container_id));
          show_table_spinner(container_id, request);

          return false;
      },

      on_standalone_sort: function(container_id, column_name, sort_on_name) {
          var container = $(ST.dialogs.jquery_id(container_id));
          var sort_names = container.data('ST.table.sort_key');
          if (sort_names) {
              sort_names.push(column_name);
          } else {
              sort_names = [column_name];
          }
          container.data('ST.table.sort_key', sort_names);

          var data = new Array();
          for (var i = 0, ie = sort_names.length; i < ie; i++) {
              data.push({
                      name: sort_on_name+':list',
                      value: sort_names[i]
                      });
          }

          var request = container_form_submit_data(container_id, data);
          request.success(set_html(container_id));
          return false;
      },

      on_batch_link: function(container_id, postfix, start, size) {
          var data = new Array();
          data.push({
              name: 'start'+postfix,
              value: start
              });
          data.push({
              name: 'size'+postfix,
              value: size
              });
          var request = container_form_submit(container_id, null, data);
          request.success(set_html(container_id));
          show_table_spinner(container_id, request);
          return false;
      }

  };

}();
