import typing

from django import template
from django.utils.safestring import SafeString
from django.utils.html import format_html, format_html_join

if typing.TYPE_CHECKING:
    from krm3.timesheet.report import ReportBlock, ReportRow, ReportCell

register = template.Library()


@register.simple_tag
def report_section(block: 'ReportBlock') -> SafeString | str:
    header = block.rows[0]

    ret = format_html(tpl_block, block.resource.last_name, block.resource.first_name)
    return ret


tpl_block = """<div class="overflow-x-auto rounded-md shadow mb-4">
                <table class="min-w-full leading-normal text-right text-zinc-900 border-2 font-semibold border-collapse">
                    <thead>
                    <tr class="bg-gray-400! dark:bg-blue-900! ">
                        <td class="text-left p-1 border border-1" colspan="2"><strong>{}</strong> {}</td>
                        <td class="p-1 text-center border border-1"></td>

                        <td class="p-1 text-center border border-1"></td>

                        <td class="p-1 text-center border border-1">

                        </td>

                        <td class="p-1 text-center border border-1">

                        </td>

                        <td class="p-1 text-center border border-1">

                        </td>

                        <td class="p-1 text-center border border-1">

                        </td>

                        <td class="p-1 text-center border border-1">
                            X
                        </td>

                        <td class="p-1 text-center border border-1">

                        </td>

                        <td class="p-1 text-center border border-1">

                        </td>

                        <td class="p-1 text-center border border-1">

                        </td>

                        <td class="p-1 text-center border border-1">

                        </td>

                        <td class="p-1 text-center border border-1">

                        </td>

                        <td class="p-1 text-center border border-1">

                        </td>

                        <td class="p-1 text-center border border-1">
                            X
                        </td>

                        <td class="p-1 text-center border border-1">

                        </td>

                        <td class="p-1 text-center border border-1">

                        </td>

                        <td class="p-1 text-center border border-1">

                        </td>

                        <td class="p-1 text-center border border-1">

                        </td>

                        <td class="p-1 text-center border border-1">

                        </td>

                        <td class="p-1 text-center border border-1">

                        </td>

                        <td class="p-1 text-center border border-1">
                            X
                        </td>

                        <td class="p-1 text-center border border-1">

                        </td>

                        <td class="p-1 text-center border border-1">

                        </td>

                        <td class="p-1 text-center border border-1">

                        </td>

                        <td class="p-1 text-center border border-1">

                        </td>

                        <td class="p-1 text-center border border-1">

                        </td>

                        <td class="p-1 text-center border border-1">

                        </td>

                        <td class="p-1 text-center border border-1">
                            X
                        </td>

                        <td class="p-1 text-center border border-1">

                        </td>

                        <td class="p-1 text-center border border-1">

                        </td>

                    </tr>

                    </thead>
                    <tbody>


                   <tr class="bg-gray-400! dark:bg-blue-900!">
                       <td class="text-left p-1 border border-1">Giorni</td>
                       <td>HH</td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Mon</p>
                           <p>1</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Tue</p>
                           <p>2</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Wed</p>
                           <p>3</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Thu</p>
                           <p>4</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Fri</p>
                           <p>5</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Sat</p>
                           <p>6</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Sun</p>
                           <p>7</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Mon</p>
                           <p>8</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Tue</p>
                           <p>9</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Wed</p>
                           <p>10</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Thu</p>
                           <p>11</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Fri</p>
                           <p>12</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Sat</p>
                           <p>13</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Sun</p>
                           <p>14</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Mon</p>
                           <p>15</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Tue</p>
                           <p>16</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Wed</p>
                           <p>17</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Thu</p>
                           <p>18</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Fri</p>
                           <p>19</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Sat</p>
                           <p>20</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Sun</p>
                           <p>21</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Mon</p>
                           <p>22</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Tue</p>
                           <p>23</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Wed</p>
                           <p>24</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Thu</p>
                           <p>25</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Fri</p>
                           <p>26</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Sat</p>
                           <p>27</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Sun</p>
                           <p>28</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Mon</p>
                           <p>29</p>
                       </td>

                       <td class="p-1 text-center border border-1 bg-yellow-600">
                           <p>Tue</p>
                           <p>30</p>
                       </td>

                   </tr>



        <tr class="bg-neutral-300 dark:bg-neutral-600!">
            <td class="border border-1 text-left p-1 ">Ore ordinarie</td>
            <td class="p-1 border border-1 text-center">48</td>
<td class="p-1 border border-1 text-center">8</td>
<td class="p-1 border border-1 text-center">8</td>
<td class="p-1 border border-1 text-center">8</td>
<td class="p-1 border border-1 text-center">8</td>
<td class="p-1 border border-1 text-center">8</td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center">4</td>
<td class="p-1 border border-1 text-center">4</td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
        </tr>



        <tr class="bg-neutral-200 dark:bg-neutral-600!">
            <td class="border border-1 text-left p-1 ">Ore notturne</td>
            <td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
        </tr>



        <tr class="bg-neutral-300 dark:bg-neutral-600!">
            <td class="border border-1 text-left p-1 ">Reperibilità</td>
            <td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
        </tr>



        <tr class="bg-neutral-200 dark:bg-neutral-600!">
            <td class="border border-1 text-left p-1 ">Viaggio</td>
            <td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
        </tr>



        <tr class="bg-neutral-300 dark:bg-neutral-600!">
            <td class="border border-1 text-left p-1 ">Ferie</td>
            <td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
        </tr>



        <tr class="bg-neutral-200 dark:bg-neutral-600!">
            <td class="border border-1 text-left p-1 ">Permessi</td>
            <td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
        </tr>



        <tr class="bg-neutral-300 dark:bg-neutral-600!">
            <td class="border border-1 text-left p-1 ">Riposo</td>
            <td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
        </tr>



        <tr class="bg-neutral-200 dark:bg-neutral-600!">
            <td class="border border-1 text-left p-1 ">Malattia</td>
            <td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
        </tr>



        <tr class="bg-neutral-300 dark:bg-neutral-600!">
            <td class="border border-1 text-left p-1 ">Ore straordinarie</td>
            <td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
        </tr>





        <tr class="bg-neutral-300 dark:bg-neutral-600!">
            <td class="border border-1 text-left p-1 ">Buoni pasto</td>
            <td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
<td class="p-1 border border-1 text-center"></td>
        </tr>


                    </tbody>
                </table>
            </div>"""
